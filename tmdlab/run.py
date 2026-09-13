"""External process supervisor: clock checks never wait for GPU telemetry.

One trial per process group and per scheduler-allocated GPU. No cluster login
or job submission is performed here. All output directories are exclusive.
"""
import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import signal
import subprocess
import sys
import threading
import time
import uuid
import psutil
from .io import read,write,sha,digest,utc
from .contracts import validate_trial

def git(*args):
    return subprocess.check_output(["git",*args],text=True).strip()

def cgroup_memory_headroom_bytes(pid, *, proc_root=Path("/proc")):
    """Return this process's finite cgroup memory headroom, or fail closed.

    Slurm's memory reservation is enforced by a task/job cgroup. Node-wide
    ``psutil.virtual_memory`` cannot prove that the reservation has headroom.
    Support the cgroup-v1 memory controller used on Rivanna and cgroup-v2 as a
    guarded fallback for portable local tests.
    """
    entries=[]
    for line in (proc_root/str(pid)/"cgroup").read_text().splitlines():
        fields=line.split(":",2)
        if len(fields)!=3: raise ValueError("malformed cgroup entry")
        entries.append(tuple(fields))
    mounts=[]
    for line in (proc_root/"mounts").read_text().splitlines():
        fields=line.split()
        if len(fields)>=4: mounts.append((fields[1],fields[2],set(fields[3].split(","))))
    def ancestors(path, root):
        if not path.is_relative_to(root): raise ValueError("cgroup path escapes mount")
        while True:
            yield path
            if path==root: return
            path=path.parent

    def finite_headroom(path, limit_name, usage_name):
        values=[]
        for candidate in ancestors(path, root):
            limit_path=candidate/limit_name; usage_path=candidate/usage_name
            if not limit_path.is_file() or not usage_path.is_file(): continue
            limit=limit_path.read_text().strip(); usage=usage_path.read_text().strip()
            if limit=="max": continue
            try: ceiling,used=int(limit),int(usage)
            except ValueError as exc: raise ValueError("noninteger cgroup memory accounting") from exc
            if ceiling<=0 or used<0: raise ValueError("invalid cgroup memory accounting")
            # cgroup v1 represents no limit with a value near INT64_MAX.
            if ceiling>=2**60: continue
            values.append(max(0,ceiling-used))
        if not values: raise ValueError("finite cgroup limit unavailable")
        # Every finite ancestor is a cap. The smallest remaining headroom is
        # the only safe allocation-level answer for this process.
        return min(values)

    for _,controllers,relative in entries:
        if "memory" not in controllers.split(","): continue
        choices=[m for m in mounts if m[1]=="cgroup" and "memory" in m[2]]
        if not choices: raise ValueError("memory cgroup mount unavailable")
        root=Path(choices[0][0]); rel=PurePosixPath(relative)
        if rel.is_absolute(): rel=PurePosixPath(*rel.parts[1:])
        path=root.joinpath(*rel.parts)
        return finite_headroom(path,"memory.limit_in_bytes","memory.usage_in_bytes")
    for hierarchy,controllers,relative in entries:
        if hierarchy!="0" or controllers: continue
        choices=[m for m in mounts if m[1]=="cgroup2"]
        if not choices: raise ValueError("cgroup-v2 mount unavailable")
        root=Path(choices[0][0]); rel=PurePosixPath(relative)
        if rel.is_absolute(): rel=PurePosixPath(*rel.parts[1:])
        path=root.joinpath(*rel.parts)
        return finite_headroom(path,"memory.max","memory.current")
    raise ValueError("memory cgroup entry unavailable")

def allocated_gpu_selector():
    """Select logical GPU zero from the scheduler-visible device namespace.

    ``SLURM_*_GPUS`` identifies a node's physical GPU (for example ``6``),
    whereas a one-GPU ``srun`` plus ``apptainer --nv`` exposes that allocation
    to CUDA and ``nvidia-smi`` as logical device zero.  The worker is pinned to
    ``cuda:0``; telemetry must query the same namespace rather than accidentally
    address a physical device which is deliberately hidden by the container.
    """
    visible=os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible is None: raise ValueError("scheduler CUDA visibility unavailable")
    selected=[item.strip() for item in visible.split(",")]
    if len(selected)!=1 or not selected[0]:
        raise ValueError("ambiguous scheduler CUDA visibility")
    return "0"

def parse_gpu_row(text):
    fields=[v.strip() for v in text.strip().split(",")]
    if len(fields)!=9 or not fields[0] or not fields[1] or not fields[2]:
        raise ValueError("malformed allocated-GPU telemetry")
    try:
        values=[float(v) for v in fields[3:]]
    except ValueError as exc: raise ValueError("non-numeric allocated-GPU telemetry") from exc
    if not all(math.isfinite(v) and v>=0 for v in values) or values[3]<=0:
        raise ValueError("invalid allocated-GPU telemetry")
    return dict(gpu_uuid=fields[0],gpu_name=fields[1],gpu_driver=fields[2],
        gpu_utilization_percent=values[0],gpu_memory_utilization_percent=values[1],
        gpu_device_memory_used_gib=values[2]/1024.,gpu_device_memory_total_gib=values[3]/1024.,
        gpu_power_watts=values[4],gpu_temperature_celsius=values[5])

def observed_accepted_updates(out):
    if out is None: return 0
    path=out/"counters.json"
    if not path.is_file(): return 0
    count=read(path).get("accepted_updates")
    if type(count) is not int or count<0: raise ValueError("invalid observed accepted-update counter")
    return count

def sample(pid,gpu,*,out=None):
    root=psutil.Process(pid)
    owned=[root,*root.children(recursive=True)]
    pids={p.pid for p in owned}
    rss=sum(p.memory_info().rss for p in owned if p.is_running())/2**30
    info=dict(monotonic=time.monotonic(),rss_gib=rss,
        host_available_gib=cgroup_memory_headroom_bytes(pid)/2**30,
        accepted_updates=observed_accepted_updates(out),gpu_owned_gib=None)
    if gpu:
        proc=subprocess.run(["nvidia-smi","--query-compute-apps=pid,used_memory","--format=csv,noheader,nounits"],text=True,capture_output=True,timeout=.75,check=True)
        memory=0.
        for row in proc.stdout.splitlines():
            if not row.strip(): continue
            process_id,value=row.split(",")
            if int(process_id.strip()) in pids: memory+=float(value.strip())/1024.
        info["gpu_owned_gib"]=memory
        selected=allocated_gpu_selector()
        device=subprocess.run(["nvidia-smi","--id",selected,
            "--query-gpu=uuid,name,driver_version,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,temperature.gpu",
            "--format=csv,noheader,nounits"],text=True,capture_output=True,timeout=.75,check=True)
        info.update(parse_gpu_row(device.stdout))
    return info

def stop_owned(process):
    if process.poll() is not None: return
    try: os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError: return
    try: process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try: os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError: pass
        process.wait(timeout=5)

def supervise(process,*,deadline,budget,gpu,out,sampler=sample):
    """Separate telemetry thread; stale/failed telemetry fails closed."""
    stop=threading.Event(); latest={"sample":None,"error":None}; started=time.monotonic()
    peak=dict(rss_gib=None,gpu_owned_gib=None,host_available_min_gib=None,samples=0)
    if gpu:
        peak.update(gpu_utilization_percent_max=None,gpu_memory_utilization_percent_max=None,
            gpu_device_memory_used_gib_max=None,gpu_device_memory_total_gib=None,
            gpu_power_watts_max=None,gpu_temperature_celsius_max=None)
    def telemetry():
        while not stop.is_set() and process.poll() is None:
            try:
                s=sample(process.pid,gpu,out=out) if sampler is sample else sampler(process.pid,gpu)
                keys=("monotonic","rss_gib","host_available_gib","accepted_updates")
                if gpu:
                    keys+=("gpu_owned_gib","gpu_utilization_percent","gpu_memory_utilization_percent",
                        "gpu_device_memory_used_gib","gpu_device_memory_total_gib","gpu_power_watts","gpu_temperature_celsius")
                for k in keys:
                    if type(s.get(k)) not in (int,float) or not math.isfinite(s[k]) or s[k]<0:
                        raise ValueError("missing/nonfinite resource telemetry: "+k)
                latest["sample"]=s
            except (psutil.NoSuchProcess,ProcessLookupError): return
            except Exception as exc: latest["error"]=type(exc).__name__+": "+str(exc); return
            stop.wait(.2)
    thread=threading.Thread(target=telemetry,daemon=True); thread.start()
    reason=None; seen=None
    try:
        with (out/"resources.ndjson").open("a") as f:
            while process.poll() is None:
                now=time.monotonic(); s=latest["sample"]
                if now>=deadline: reason="model_deadline"
                elif latest["error"]: reason="telemetry_failure: "+latest["error"]
                elif now-(s["monotonic"] if s else started)>1.: reason="telemetry_stale_over_1s"
                elif s:
                    if s["rss_gib"]>budget["rss_gib"] or s["host_available_gib"]<budget["host_available_gib"] or gpu and s["gpu_owned_gib"]>budget["gpu_gib"]: reason="resource_limit"
                    if s["monotonic"]!=seen:
                        seen=s["monotonic"]; peak["samples"]+=1
                        peak["rss_gib"]=s["rss_gib"] if peak["rss_gib"] is None else max(peak["rss_gib"],s["rss_gib"])
                        peak["host_available_min_gib"]=s["host_available_gib"] if peak["host_available_min_gib"] is None else min(peak["host_available_min_gib"],s["host_available_gib"])
                        if gpu:
                            peak["gpu_owned_gib"]=max(peak["gpu_owned_gib"] or 0.,s["gpu_owned_gib"])
                            for key in ("gpu_utilization_percent","gpu_memory_utilization_percent","gpu_device_memory_used_gib","gpu_power_watts","gpu_temperature_celsius"):
                                peak[key+"_max"]=max(peak[key+"_max"] or 0.,s[key])
                            peak["gpu_device_memory_total_gib"]=s["gpu_device_memory_total_gib"]
                        f.write(json.dumps(s,allow_nan=False)+"\n"); f.flush()
                if reason:
                    stop_owned(process); break
                time.sleep(.1)
    finally:
        stop.set(); thread.join(timeout=1)
    if peak["samples"]==0 and reason is None:
        reason="telemetry_failure: "+latest["error"] if latest["error"] else "telemetry_missing_no_samples"
    return dict(stop_reason=reason,peaks=peak,resource_telemetry_status="sampled" if peak["samples"] else "unknown_no_samples",resource_peaks_are_sampled_not_continuous=True,telemetry_staleness_limit_seconds=1.,model_stop_escalation_seconds=2.,exit_code=process.wait())

def main(args):
    trial=validate_trial(read(args.trial)); budget=trial["budget"]
    root=Path(git("rev-parse","--show-toplevel")); commit=git("rev-parse","HEAD")
    if git("status","--porcelain"): raise ValueError("commit all code/spec changes before a scientific run")
    if args.device not in ("cpu","cuda:0") or trial["execution_class"]!=("cpu" if args.device=="cpu" else "gpu"):
        raise ValueError("device differs from preregistered execution class")
    if "SLURM_CPUS_PER_TASK" in os.environ and budget["cpu_threads"]>int(os.environ["SLURM_CPUS_PER_TASK"]):
        raise ValueError("trial CPU threads exceed scheduler allocation")
    if not args.trial.resolve().is_relative_to(root): raise ValueError("trial must be in this pinned git checkout")
    if args.device.startswith("cuda") and "SLURM_JOB_ID" in os.environ and not os.environ.get("CUDA_VISIBLE_DEVICES"):
        raise ValueError("no scheduler-assigned CUDA visibility; do not overwrite it")
    if args.claim is None: raise ValueError("supply a durable claim receipt; see docs/COORDINATION.md")
    claim=read(args.claim)
    if claim["trial_id"]!=trial["trial_id"] or claim["trial_sha256"]!=sha(args.trial) or claim["code_commit"]!=commit:
        raise ValueError("claim/spec/code mismatch")
    args.out.mkdir(parents=True,exist_ok=False)
    def terminate(*_): raise KeyboardInterrupt("supervisor termination requested")
    signal.signal(signal.SIGTERM,terminate)
    t0=time.monotonic(); epoch=time.time()
    env=os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONNOUSERSITE="1",OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1",CUBLAS_WORKSPACE_CONFIG=":4096:8")
    launch=dict(schema="tmd-launch-v1",run_id=trial["trial_id"]+"-"+uuid.uuid4().hex[:12],trial_id=trial["trial_id"],trial_sha256=sha(args.trial),code_commit=commit,bundle_identity=trial["bundle_identity"],claim=claim,t0_utc=utc(),t0_epoch=epoch,t0_monotonic=t0,model_deadline_monotonic=t0+budget["segment_seconds"],final_deadline_monotonic=t0+budget["total_seconds"],budget=budget,device=args.device,platform=platform.platform(),python=sys.version,slurm={k:os.environ.get(k) for k in ("SLURM_JOB_ID","SLURM_ARRAY_JOB_ID","SLURM_ARRAY_TASK_ID","SLURM_CPUS_PER_TASK","SLURM_JOB_GPUS","CUDA_VISIBLE_DEVICES")})
    write(args.out/"launch.json",launch)
    write(args.out/"trial.json",trial)
    command=[sys.executable,"-m","tmdlab.worker","--trial",str(args.trial.resolve()),"--bundle",str(args.bundle.resolve()),"--out",str(args.out.resolve()),"--device",args.device]
    process=None
    try:
        with (args.out/"worker.log").open("x") as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
            write(args.out/"owner.json",dict(supervisor_pid=os.getpid(),worker_pid=process.pid,owned_process_group=process.pid))
            outcome=supervise(process,deadline=launch["model_deadline_monotonic"],budget=budget,gpu=args.device.startswith("cuda"),out=args.out)
    except BaseException:
        if process is not None: stop_owned(process)
        raise
    write(args.out/"supervisor.json",dict(outcome,end_utc=utc(),elapsed_seconds=time.monotonic()-t0))
    remaining=launch["final_deadline_monotonic"]-time.monotonic()
    audit_code=None
    if remaining>0:
        try:
            with (args.out/"audit.log").open("x") as log:
                audit_code=subprocess.run([sys.executable,"-m","tmdlab.audit","--bundle",str(args.bundle.resolve()),"--out",str(args.out.resolve())],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=remaining).returncode
        except subprocess.TimeoutExpired: audit_code=124
    write(args.out/"cleanup.json",dict(worker_reaped=process.poll() is not None,audit_exit_code=audit_code,end_utc=utc(),elapsed_seconds=time.monotonic()-t0,model_dispatch_cutoff_enforced_by_worker_guard=True))
    print(json.dumps(dict(output=str(args.out),worker=outcome["exit_code"],audit=audit_code)))
    return 0 if outcome["exit_code"]==0 and audit_code==0 and outcome["stop_reason"] is None else 2

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trial",type=Path,required=True); p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True); p.add_argument("--device",required=True); p.add_argument("--claim",type=Path)
    raise SystemExit(main(p.parse_args()))
