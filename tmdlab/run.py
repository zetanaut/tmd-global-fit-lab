"""External process supervisor: clock checks never wait for GPU telemetry.

One trial per process group and per scheduler-allocated GPU. No cluster login
or job submission is performed here. All output directories are exclusive.
"""
import argparse
import json
import math
import os
from pathlib import Path
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

def sample(pid,gpu):
    root=psutil.Process(pid)
    owned=[root,*root.children(recursive=True)]
    pids={p.pid for p in owned}
    rss=sum(p.memory_info().rss for p in owned if p.is_running())/2**30
    info=dict(monotonic=time.monotonic(),rss_gib=rss,host_available_gib=psutil.virtual_memory().available/2**30,gpu_owned_gib=None)
    if gpu:
        proc=subprocess.run(["nvidia-smi","--query-compute-apps=pid,used_memory","--format=csv,noheader,nounits"],text=True,capture_output=True,timeout=.75,check=True)
        memory=0.
        for row in proc.stdout.splitlines():
            if not row.strip(): continue
            process_id,value=row.split(",")
            if int(process_id.strip()) in pids: memory+=float(value.strip())/1024.
        info["gpu_owned_gib"]=memory
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
    peak=dict(rss_gib=0.,gpu_owned_gib=None,host_available_min_gib=None,samples=0)
    def telemetry():
        while not stop.is_set() and process.poll() is None:
            try:
                s=sampler(process.pid,gpu)
                for k in ("monotonic","rss_gib","host_available_gib",*( ["gpu_owned_gib"] if gpu else [])):
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
                        peak["rss_gib"]=max(peak["rss_gib"],s["rss_gib"])
                        peak["host_available_min_gib"]=s["host_available_gib"] if peak["host_available_min_gib"] is None else min(peak["host_available_min_gib"],s["host_available_gib"])
                        if gpu: peak["gpu_owned_gib"]=max(peak["gpu_owned_gib"] or 0.,s["gpu_owned_gib"])
                        f.write(json.dumps(s,allow_nan=False)+"\n"); f.flush()
                if reason:
                    stop_owned(process); break
                time.sleep(.1)
    finally:
        stop.set(); thread.join(timeout=1)
    return dict(stop_reason=reason,peaks=peak,resource_peaks_are_sampled_not_continuous=True,telemetry_staleness_limit_seconds=1.,model_stop_escalation_seconds=2.,exit_code=process.wait())

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
