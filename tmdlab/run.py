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
from .contracts import validate_trial,RESUME_TRAJECTORY_LIMITS
from .gpu_telemetry import NvmlDevice,canonical_uuid
from .restart import elapsed_before,segment_allowance

_gpu_local=threading.local()
_progress_local=threading.local()

def paired_launch_binding(trial, trial_path, claim, claim_path, commit, bundle, device, deadline):
    """Create the exact receipt consumed by the W03 child evaluator."""
    entry,_=bundle.checkpoint(trial['start_checkpoint'])
    source_sha=sha(bundle.file(entry['path']))
    if source_sha!=trial['paired_start']['source_checkpoint_sha256']:
        raise ValueError('paired feasibility source checkpoint hash mismatch')
    budget=trial['budget']; start=trial['paired_start']
    return dict(schema='tmd-paired-width-feasibility-launch-v1',trial_id=trial['trial_id'],
        trial_sha256=sha(trial_path),code_commit=commit,claim_commit=claim['claim_commit'],
        claim_sha256=sha(claim_path),spec_sha256=sha(trial_path),bundle_identity=trial['bundle_identity'],
        source_checkpoint=trial['start_checkpoint'],source_checkpoint_sha256=source_sha,device=device,
        seeds=start['seeds'],radius=start['radius'],min_diversity_rms=start['min_diversity_rms'],
        cache_gib=budget['cache_gib'],max_forwards=budget['forwards'],max_full_calls=budget['full_calls'],
        seconds=budget['segment_seconds'],model_deadline_monotonic=deadline)

def git(*args):
    return subprocess.check_output(["git",*args],text=True).strip()

def _memory_cgroup_scope(pid, proc_root):
    """Resolve the worker's memory controller, retaining its full ancestor scope."""
    entries=[]
    for line in (proc_root/str(pid)/"cgroup").read_text().splitlines():
        fields=line.split(":",2)
        if len(fields)!=3: raise ValueError("malformed cgroup entry")
        entries.append(tuple(fields))
    mounts=[]
    for line in (proc_root/"mounts").read_text().splitlines():
        fields=line.split()
        if len(fields)>=4: mounts.append((fields[1],fields[2],set(fields[3].split(","))))
    for _,controllers,relative in entries:
        if "memory" not in controllers.split(","): continue
        choices=[m for m in mounts if m[1]=="cgroup" and "memory" in m[2]]
        if not choices: raise ValueError("memory cgroup mount unavailable")
        root=Path(choices[0][0]); rel=PurePosixPath(relative)
        if '..' in rel.parts: raise ValueError("cgroup path escapes mount")
        if rel.is_absolute(): rel=PurePosixPath(*rel.parts[1:])
        path=root.joinpath(*rel.parts)
        return root,path,"memory.limit_in_bytes","memory.usage_in_bytes"
    for hierarchy,controllers,relative in entries:
        if hierarchy!="0" or controllers: continue
        choices=[m for m in mounts if m[1]=="cgroup2"]
        if not choices: raise ValueError("cgroup-v2 mount unavailable")
        root=Path(choices[0][0]); rel=PurePosixPath(relative)
        if '..' in rel.parts: raise ValueError("cgroup path escapes mount")
        if rel.is_absolute(): rel=PurePosixPath(*rel.parts[1:])
        path=root.joinpath(*rel.parts)
        return root,path,"memory.max","memory.current"
    raise ValueError("memory cgroup entry unavailable")

def _finite_cgroup_headroom(scope, required=()):
    root,path,limit_name,usage_name=scope
    if not path.is_relative_to(root): raise ValueError("cgroup path escapes mount")
    values={}
    while True:
        limit_path=path/limit_name; usage_path=path/usage_name
        if limit_path.is_file() and usage_path.is_file():
            limit=limit_path.read_text().strip(); usage=usage_path.read_text().strip()
            if limit!="max":
                try: ceiling,used=int(limit),int(usage)
                except ValueError as exc: raise ValueError("noninteger cgroup memory accounting") from exc
                if ceiling<=0 or used<0: raise ValueError("invalid cgroup memory accounting")
                if ceiling<2**60: values[path]=max(0,ceiling-used)
        if path==root: break
        path=path.parent
    if not values or any(path not in values for path in required):
        raise ValueError("finite cgroup limit unavailable")
    return min(values.values()),tuple(values)

def cgroup_memory_headroom_bytes(pid, *, proc_root=Path("/proc")):
    """One-shot finite headroom, including every finite worker ancestor cap."""
    return _finite_cgroup_headroom(_memory_cgroup_scope(pid,proc_root))[0]

def _process_cgroup_identity(pid, proc_root):
    # /proc/PID/stat field 9 is flags, field 22 is process start time. comm
    # can contain spaces and ')', so split after its final closing parenthesis.
    text=(proc_root/str(pid)/"stat").read_text()
    prefix,separator,suffix=text.rpartition(')')
    fields=suffix.split()
    if not separator or len(fields)<20 or prefix.split('(',1)[0].strip()!=str(pid):
        raise ValueError("invalid owned process identity")
    return int(fields[19]),int(fields[6])

class CgroupMemoryBinding:
    """Pin scope, never readings; tolerate only verified v1 PF_EXITING→root.

    This retains stricter worker/ancestor limits rather than substituting the
    supervisor's possibly broader cgroup. Live migration and scope replacement
    fail closed. Every sample rereads the current limits and usage.
    """
    def __init__(self,pid,*,proc_root=Path('/proc')):
        self.pid=pid; self.proc_root=proc_root
        self.start,flags=_process_cgroup_identity(pid,proc_root)
        self.scope=_memory_cgroup_scope(pid,proc_root)
        if flags&4: raise ValueError('cannot bind an already exiting worker')
        _,self.required=_finite_cgroup_headroom(self.scope)
        paths=set(self.required)|{self.scope[1]}
        self.identities={path:self._directory_identity(path) for path in paths}
        self.exit_transition=False
        self.read()  # Verify membership/identity stayed stable while binding.

    @staticmethod
    def _directory_identity(path):
        stat=path.stat()
        return stat.st_dev,stat.st_ino

    def read(self):
        scope=_memory_cgroup_scope(self.pid,self.proc_root)
        start,flags=_process_cgroup_identity(self.pid,self.proc_root)
        if start!=self.start: raise ValueError('owned process identity changed')
        root,path,limit_name,usage_name=self.scope
        changed=scope!=self.scope
        exiting_root=(limit_name=='memory.limit_in_bytes' and path!=root
            and scope==(root,root,limit_name,usage_name) and bool(flags&4))
        if changed and not exiting_root: raise ValueError('worker memory cgroup migration')
        for candidate,identity in self.identities.items():
            if self._directory_identity(candidate)!=identity:
                raise ValueError('bound memory cgroup replaced')
        value,_=_finite_cgroup_headroom(self.scope,self.required)
        self.exit_transition=exiting_root
        return value

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

class AcceptedUpdateProgress:
    """Best-effort progress metadata, never a substitute for resource telemetry.

    The worker updates ``counters.json`` while it commits work.  Observed live
    reads can return ENOENT while those shared-file updates occur, even though
    mandatory process, cgroup, and GPU readings are fresh.  Preserve the last
    monotonic counter in that case, but make its stale or unavailable state
    explicit instead of inventing zero progress or stopping the worker.
    """
    def __init__(self,out):
        self.out=out
        self.last=None
        self.cached_result=None
        self.query_thread=None
        self.last_query_started=None

    def unavailable(self,kind,error=None):
        status=("stale_" if self.last is not None else "unavailable_")+kind
        return dict(accepted_updates=self.last,accepted_updates_status=status,
            accepted_updates_error=error)

    def observe(self):
        if self.out is None: return self.unavailable("no_output")
        try:
            value=read(self.out/"counters.json").get("accepted_updates")
        except FileNotFoundError:
            return self.unavailable("missing","FileNotFoundError")
        except Exception as exc:
            return self.unavailable("read_error",type(exc).__name__)
        if type(value) is not int or value<0:
            return self.unavailable("invalid","invalid accepted-update counter")
        if self.last is not None and value<self.last:
            return self.unavailable("nonmonotonic","accepted-update counter decreased")
        self.last=value
        return dict(accepted_updates=value,accepted_updates_status="fresh",
            accepted_updates_error=None)

    def _query(self):
        result=self.observe()
        result['accepted_updates_read_monotonic']=time.monotonic()
        self.cached_result=result

    def _start_query(self,now):
        if self.out is None: return
        if self.query_thread is not None and self.query_thread.is_alive(): return
        if self.last_query_started is not None and now-self.last_query_started<.2:return
        self.last_query_started=now
        self.query_thread=threading.Thread(target=self._query,daemon=True)
        self.query_thread.start()

    def cached(self):
        """Return progress cache and request one read without waiting for it."""
        now=time.monotonic(); result=self.cached_result
        if result is None:
            result=self.unavailable("pending")
            read_at=None
        else:
            result=dict(result)
            read_at=result['accepted_updates_read_monotonic']
        result['accepted_updates_read_monotonic']=read_at
        result['accepted_updates_read_age_seconds']=(None if read_at is None
            else max(0.,now-read_at))
        thread=self.query_thread
        if thread is not None and thread.is_alive():
            status=result['accepted_updates_status']
            if result['accepted_updates'] is None:
                result['accepted_updates_status']=status+'_refreshing'
            elif status=='fresh': result['accepted_updates_status']='stale_refreshing'
        result['accepted_updates_query_in_flight']=bool(thread and thread.is_alive())
        self._start_query(now)
        return result

def observed_accepted_updates(out,progress=None):
    """Read optional worker progress with explicit availability metadata."""
    return (progress or AcceptedUpdateProgress(out)).observe()

def cached_accepted_updates(out,progress=None):
    if progress is None:
        progress=getattr(_progress_local,'progress',None)
        if progress is None or progress.out!=out:
            progress=AcceptedUpdateProgress(out); _progress_local.progress=progress
    return progress.cached()

def sample(pid,gpu,*,out=None,memory_binding=None,progress=None):
    sample_started=time.monotonic()
    root=psutil.Process(pid)
    owned=[root,*root.children(recursive=True)]
    pids={p.pid for p in owned}
    rss=sum(p.memory_info().rss for p in owned if p.is_running())/2**30
    info=dict(monotonic=time.monotonic(),rss_gib=rss,
        host_available_gib=(memory_binding.read() if memory_binding is not None
            else cgroup_memory_headroom_bytes(pid))/2**30,gpu_owned_gib=None)
    info.update(cached_accepted_updates(out,progress))
    if memory_binding is not None:
        info.update(cgroup_memory_path=str(memory_binding.scope[1]),
            cgroup_worker_exit_transition=memory_binding.exit_transition)
    if gpu:
        uuid=os.environ.get('TMD_GPU_UUID')
        if uuid:
            if not hasattr(_gpu_local,'device') or _gpu_local.device.uuid!=canonical_uuid(uuid):
                _gpu_local.device=NvmlDevice(uuid,async_optional=True)
            info.update(_gpu_local.device.sample(pids))
            info['sample_duration_seconds']=time.monotonic()-sample_started
            info['monotonic']=time.monotonic()
            return info
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
    info['sample_duration_seconds']=time.monotonic()-sample_started
    info['monotonic']=time.monotonic()
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
    stop=threading.Event(); latest={"sample":None,"error":None,"terminal_error":None}; started=time.monotonic()
    peak=dict(rss_gib=None,gpu_owned_gib=None,host_available_min_gib=None,samples=0)
    if gpu:
        peak.update(gpu_utilization_percent_max=None,gpu_memory_utilization_percent_max=None,
            gpu_device_memory_used_gib_max=None,gpu_device_memory_total_gib=None,
            gpu_power_watts_max=None,gpu_temperature_celsius_max=None)
    def telemetry():
        memory_binding=None
        progress=AcceptedUpdateProgress(out)
        while not stop.is_set() and process.poll() is None:
            try:
                if sampler is sample:
                    if memory_binding is None: memory_binding=CgroupMemoryBinding(process.pid)
                    s=sample(process.pid,gpu,out=out,memory_binding=memory_binding,progress=progress)
                else: s=sampler(process.pid,gpu)
                keys=("monotonic","rss_gib","host_available_gib")
                if gpu:
                    keys+=("gpu_owned_gib","gpu_device_memory_used_gib","gpu_device_memory_total_gib")
                    for key in ('gpu_utilization_percent','gpu_memory_utilization_percent','gpu_power_watts','gpu_temperature_celsius'):
                        if s.get(key) is not None:keys+=(key,)
                for k in keys:
                    if type(s.get(k)) not in (int,float) or not math.isfinite(s[k]) or s[k]<0:
                        raise ValueError("missing/nonfinite resource telemetry: "+k)
                latest["sample"]=s
            except (psutil.NoSuchProcess,ProcessLookupError): return
            except Exception as exc:
                error=type(exc).__name__+': '+str(exc)
                # A worker can exit between the loop's poll and /proc/cgroup
                # reads. Reap/check that SAME owned process before treating an
                # unavailable sample as a failure of live-worker monitoring.
                if process.poll() is not None:latest['terminal_error']=error
                else:latest['error']=error
                return
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
                                if s.get(key) is not None:peak[key+"_max"]=max(peak[key+"_max"] or 0.,s[key])
                            peak["gpu_device_memory_total_gib"]=s["gpu_device_memory_total_gib"]
                        f.write(json.dumps(s,allow_nan=False)+"\n"); f.flush()
                if reason:
                    stop_owned(process); break
                time.sleep(.1)
    finally:
        stop.set(); thread.join(timeout=1)
    if peak["samples"]==0 and reason is None:
        reason="telemetry_failure: "+latest["error"] if latest["error"] else "telemetry_missing_no_samples"
    return dict(stop_reason=reason,peaks=peak,resource_telemetry_status="sampled" if peak["samples"] else "unknown_no_samples",resource_peaks_are_sampled_not_continuous=True,telemetry_staleness_limit_seconds=1.,model_stop_escalation_seconds=2.,terminal_sample_unavailable_after_owned_exit=latest['terminal_error'],exit_code=process.wait())

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
    prior_seconds=0.; model_seconds=budget['segment_seconds']
    if trial.get('execution_policy') in RESUME_TRAJECTORY_LIMITS:
        manifest=read(root/'restarts'/(trial['start_checkpoint'][8:]+'.json'))
        prior_seconds=elapsed_before(root,manifest)
        model_seconds=segment_allowance(trial,prior_seconds)
    paired=trial.get('execution_policy')=='paired-feasibility-v1'
    args.out.mkdir(parents=True,exist_ok=False)
    def terminate(*_): raise KeyboardInterrupt("supervisor termination requested")
    signal.signal(signal.SIGTERM,terminate)
    t0=time.monotonic(); epoch=time.time()
    env=os.environ.copy()
    if trial.get('execution_policy') in RESUME_TRAJECTORY_LIMITS and args.device.startswith('cuda'):
        # Launch wrapper proves CUDA-0/NVML equality once, before accepting a
        # trial. A numeric Slurm index is never substituted for this UUID.
        canonical_uuid(env.get('TMD_GPU_UUID',''))
        write(args.out/'gpu-identity.json',dict(uuid=env['TMD_GPU_UUID'],
            logical_cuda_device=args.device,slurm_physical_devices=env.get('SLURM_STEP_GPUS') or env.get('SLURM_JOB_GPUS')))
    env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONNOUSERSITE="1",OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1",CUBLAS_WORKSPACE_CONFIG=":4096:8")
    launch=dict(schema="tmd-launch-v1",run_id=trial["trial_id"]+"-"+uuid.uuid4().hex[:12],trial_id=trial["trial_id"],trial_sha256=sha(args.trial),code_commit=commit,bundle_identity=trial["bundle_identity"],claim=claim,t0_utc=utc(),t0_epoch=epoch,t0_monotonic=t0,model_deadline_monotonic=t0+budget["segment_seconds"],final_deadline_monotonic=t0+budget["total_seconds"],budget=budget,device=args.device,platform=platform.platform(),python=sys.version,slurm={k:os.environ.get(k) for k in ("SLURM_JOB_ID","SLURM_ARRAY_JOB_ID","SLURM_ARRAY_TASK_ID","SLURM_CPUS_PER_TASK","SLURM_JOB_GPUS","CUDA_VISIBLE_DEVICES")})
    if trial.get('execution_policy') in RESUME_TRAJECTORY_LIMITS:
        launch.update(model_deadline_monotonic=t0+model_seconds,
            model_seconds_before=prior_seconds,effective_segment_seconds=model_seconds,
            trajectory_budget=trial['trajectory_budget'])
    write(args.out/"launch.json",launch)
    write(args.out/"trial.json",trial)
    if paired:
        # This check occurs in the supervising, pinned and clean checkout
        # before the child gets a non-forgeable binding.  The child repeats it
        # against the mounted bundle after it starts.
        from .bundle import Bundle
        binding=paired_launch_binding(trial,args.trial,claim,args.claim,commit,Bundle(args.bundle),args.device,
            launch['model_deadline_monotonic'])
        binding_path=args.out/'paired-launch-binding.json'; write(binding_path,binding)
        command=[sys.executable,'-m','tmdlab.paired_feasibility','--bundle',str(args.bundle.resolve()),
            '--source-checkpoint',trial['start_checkpoint'],'--device',args.device,'--seeds',*map(str,trial['paired_start']['seeds']),
            '--radius',str(trial['paired_start']['radius']),'--min-diversity-rms',str(trial['paired_start']['min_diversity_rms']),
            '--cache-gib',str(budget['cache_gib']),'--max-forwards',str(budget['forwards']),'--max-full-calls',str(budget['full_calls']),
            '--seconds',str(budget['segment_seconds']),'--launch-binding',str(binding_path.resolve()),'--out',str((args.out/'worker').resolve())]
    else:
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
