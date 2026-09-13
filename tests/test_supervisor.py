import json
import subprocess
import sys
import threading
import time
import pytest
from tmdlab.io import write
from tmdlab.run import (AcceptedUpdateProgress,supervise,stop_owned,
    cgroup_memory_headroom_bytes,allocated_gpu_selector,parse_gpu_row)

BUDGET=dict(rss_gib=48,gpu_gib=20,host_available_gib=8)

def child(seconds=10):
    return subprocess.Popen([sys.executable,"-c",f"import time; time.sleep({seconds})"],start_new_session=True)

def healthy(pid,gpu):
    return dict(monotonic=time.monotonic(),rss_gib=1.,host_available_gib=16.,accepted_updates=0,gpu_owned_gib=2. if gpu else None)

def test_deadline_does_not_wait_for_slow_sampler(tmp_path):
    p=child();started=time.monotonic()
    def slow(pid,gpu):time.sleep(2.5);return healthy(pid,gpu)
    try:result=supervise(p,deadline=started+.15,budget=BUDGET,gpu=False,out=tmp_path,sampler=slow)
    finally:stop_owned(p)
    assert result["stop_reason"]=="model_deadline"
    # Thread shutdown may consume1s; process stop is already recorded/reaped.
    assert time.monotonic()-started<2.
    assert p.poll() is not None

def test_stale_telemetry_fails_closed(tmp_path):
    p=child()
    def stale(pid,gpu):return dict(healthy(pid,gpu),monotonic=time.monotonic()-2)
    try:r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=stale)
    finally:stop_owned(p)
    assert r["stop_reason"]=="telemetry_stale_over_1s"

def test_malformed_telemetry_fails_closed(tmp_path):
    p=child()
    def malformed(pid,gpu):return dict(healthy(pid,gpu),rss_gib=float("nan"))
    try:r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=malformed)
    finally:stop_owned(p)
    assert r["stop_reason"].startswith("telemetry_failure")

def test_optional_progress_missing_during_counter_read_is_explicit_not_fatal(tmp_path,monkeypatch):
    """A replace race after the old lookup must not kill fresh memory telemetry."""
    progress=AcceptedUpdateProgress(tmp_path)
    import tmdlab.run as run
    original=run.read
    def missing(path):
        if path.name=='counters.json': raise FileNotFoundError(path)
        return original(path)
    monkeypatch.setattr(run,'read',missing)
    observed=progress.observe()
    assert observed==dict(accepted_updates=None,accepted_updates_status='unavailable_missing',
        accepted_updates_error='FileNotFoundError')

def test_optional_progress_missing_start_recovers_and_never_invents_zero(tmp_path):
    progress=AcceptedUpdateProgress(tmp_path)
    assert progress.observe()['accepted_updates'] is None
    assert progress.observe()['accepted_updates_status']=='unavailable_missing'
    write(tmp_path/'counters.json',dict(accepted_updates=3))
    assert progress.observe()==dict(accepted_updates=3,accepted_updates_status='fresh',
        accepted_updates_error=None)

def test_optional_progress_read_error_is_explicit_and_recovers(tmp_path,monkeypatch):
    progress=AcceptedUpdateProgress(tmp_path)
    import tmdlab.run as run
    original=run.read
    def unreadable(path):
        if path.name=='counters.json': raise OSError('transient read failure')
        return original(path)
    monkeypatch.setattr(run,'read',unreadable)
    assert progress.observe()==dict(accepted_updates=None,accepted_updates_status='unavailable_read_error',
        accepted_updates_error='OSError')
    monkeypatch.setattr(run,'read',original)
    write(tmp_path/'counters.json',dict(accepted_updates=4))
    assert progress.observe()['accepted_updates_status']=='fresh'

def test_optional_progress_persistent_unavailable_retains_stale_monotonic_value(tmp_path):
    write(tmp_path/'counters.json',dict(accepted_updates=5))
    progress=AcceptedUpdateProgress(tmp_path)
    assert progress.observe()['accepted_updates']==5
    (tmp_path/'counters.json').unlink()
    first=progress.observe(); second=progress.observe()
    for observed in (first,second):
        assert observed['accepted_updates']==5
        assert observed['accepted_updates_status']=='stale_missing'
        assert observed['accepted_updates_error']=='FileNotFoundError'

def test_optional_progress_malformed_or_decreasing_counter_is_explicit(tmp_path):
    progress=AcceptedUpdateProgress(tmp_path)
    write(tmp_path/'counters.json',dict(accepted_updates='bad'))
    assert progress.observe()==dict(accepted_updates=None,accepted_updates_status='unavailable_invalid',
        accepted_updates_error='invalid accepted-update counter')
    write(tmp_path/'counters.json',dict(accepted_updates=7))
    assert progress.observe()['accepted_updates_status']=='fresh'
    write(tmp_path/'counters.json',dict(accepted_updates=6))
    observed=progress.observe()
    assert observed==dict(accepted_updates=7,accepted_updates_status='stale_nonmonotonic',
        accepted_updates_error='accepted-update counter decreased')

def test_supervisor_keeps_fresh_mandatory_telemetry_when_progress_is_unavailable(tmp_path):
    p=child(.5)
    def mandatory_only(pid,gpu):
        return dict(monotonic=time.monotonic(),rss_gib=1.,host_available_gib=16.,gpu_owned_gib=None,
            accepted_updates=None,accepted_updates_status='unavailable_missing',
            accepted_updates_error='FileNotFoundError')
    try:r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=mandatory_only)
    finally:stop_owned(p)
    assert r['stop_reason'] is None and r['peaks']['samples']>=1

def test_builtin_supervisor_does_not_wait_for_blocked_optional_progress_read(tmp_path,monkeypatch):
    """A blocked counters read cannot make fresh mandatory samples stale."""
    import tmdlab.run as run
    entered=threading.Event()
    class Owned:
        pid=4242; code=None; calls=0
        def poll(self): return self.code
        def wait(self,timeout=None): return self.code
    owned=Owned()
    class Binding:
        scope=(None,tmp_path/'bound',None,None); exit_transition=False
        def __init__(self,pid): assert pid==owned.pid
        def read(self): return 16*2**30
    class Process:
        def __init__(self,pid): assert pid==owned.pid; self.pid=pid
        def children(self,recursive): return []
        def is_running(self): return True
        def memory_info(self):
            owned.calls+=1
            if owned.calls>=8: owned.code=0
            return type('Memory',(),dict(rss=2**30))()
    def blocked(path):
        if path.name=='counters.json':
            entered.set(); time.sleep(2.2)
            return dict(accepted_updates=5)
        raise AssertionError('unexpected progress read')
    monkeypatch.setattr(run,'CgroupMemoryBinding',Binding)
    monkeypatch.setattr(run.psutil,'Process',Process)
    monkeypatch.setattr(run,'read',blocked)
    monkeypatch.setattr(run,'stop_owned',lambda process:(_ for _ in ()).throw(
        AssertionError('healthy worker stopped')))
    result=run.supervise(owned,deadline=time.monotonic()+3,
        budget=dict(rss_gib=4,host_available_gib=8),gpu=False,out=tmp_path)
    assert entered.wait(.5)
    assert result['stop_reason'] is None and result['peaks']['samples']>=7
    rows=[json.loads(line) for line in (tmp_path/'resources.ndjson').read_text().splitlines()]
    assert all('accepted_updates_read_monotonic' in row and 'accepted_updates_read_age_seconds' in row for row in rows)

def test_builtin_supervisor_keeps_mandatory_memory_failure_fatal_with_progress_reading(tmp_path,monkeypatch):
    import tmdlab.run as run
    entered=threading.Event(); stopped=[]
    class Owned:
        pid=4242; code=None
        def poll(self): return self.code
        def wait(self,timeout=None): return self.code
    owned=Owned()
    class Binding:
        scope=(None,tmp_path/'bound',None,None); exit_transition=False
        def __init__(self,pid): self.calls=0
        def read(self):
            self.calls+=1
            if self.calls==2:
                assert entered.wait(.5)
                raise ValueError('finite cgroup limit unavailable')
            return 16*2**30
    class Process:
        def __init__(self,pid): assert pid==owned.pid; self.pid=pid
        def children(self,recursive): return []
        def is_running(self): return True
        def memory_info(self): return type('Memory',(),dict(rss=2**30))()
    def blocked(path):
        assert path.name=='counters.json'; entered.set(); time.sleep(2.2)
        return dict(accepted_updates=5)
    def stop(process):
        stopped.append(process); process.code=-15
    monkeypatch.setattr(run,'CgroupMemoryBinding',Binding)
    monkeypatch.setattr(run.psutil,'Process',Process)
    monkeypatch.setattr(run,'read',blocked)
    monkeypatch.setattr(run,'stop_owned',stop)
    result=run.supervise(owned,deadline=time.monotonic()+3,
        budget=dict(rss_gib=4,host_available_gib=8),gpu=False,out=tmp_path)
    assert result['stop_reason'].startswith('telemetry_failure: ValueError: finite cgroup')
    assert stopped==[owned]

def test_limit_stops_only_owned_process(tmp_path):
    p=child();unrelated=child()
    def high(pid,gpu):return dict(healthy(pid,gpu),rss_gib=49.)
    try:
        r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=high)
        assert r["stop_reason"]=="resource_limit"
        assert unrelated.poll() is None
    finally:stop_owned(p);stop_owned(unrelated)

def test_real_sample_peaks_persist(tmp_path):
    p=child(.6);count=0
    def rising(pid,gpu):
        nonlocal count
        count+=1
        return dict(healthy(pid,gpu),rss_gib=float(count))
    try:r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=rising)
    finally:stop_owned(p)
    assert r["stop_reason"] is None
    assert r["peaks"]["rss_gib"]>=2
    assert r["peaks"]["samples"]>=2
    assert (tmp_path/"resources.ndjson").read_text().strip()

def test_v1_cgroup_headroom_uses_process_cgroup_not_node_memory(tmp_path):
    proc=tmp_path/'proc'; pid=4242; mount=tmp_path/'memory'
    path=mount/'slurm'/'job_7'/'step_0'; path.mkdir(parents=True)
    (proc/str(pid)).mkdir(parents=True)
    (proc/str(pid)/'cgroup').write_text('9:memory:/slurm/job_7/step_0\n')
    (proc/'mounts').write_text(f'none {mount} cgroup rw,memory 0 0\n')
    (path/'memory.limit_in_bytes').write_text(str(16*2**30))
    (path/'memory.usage_in_bytes').write_text(str(3*2**30))
    assert cgroup_memory_headroom_bytes(pid,proc_root=proc)==13*2**30

def test_cgroup_headroom_fails_closed_without_finite_limit(tmp_path):
    proc=tmp_path/'proc'; pid=4242; mount=tmp_path/'memory'
    path=mount/'slurm'/'job_7'; path.mkdir(parents=True)
    (proc/str(pid)).mkdir(parents=True)
    (proc/str(pid)/'cgroup').write_text('9:memory:/slurm/job_7\n')
    (proc/'mounts').write_text(f'none {mount} cgroup rw,memory 0 0\n')
    (path/'memory.limit_in_bytes').write_text(str(2**61))
    (path/'memory.usage_in_bytes').write_text('1')
    with pytest.raises(ValueError,match='finite'):
        cgroup_memory_headroom_bytes(pid,proc_root=proc)

def test_cgroup_headroom_uses_finite_job_parent_when_step_is_unlimited(tmp_path):
    proc=tmp_path/'proc'; pid=4242; mount=tmp_path/'memory'
    job=mount/'slurm'/'job_7'; step=job/'step_0'; step.mkdir(parents=True)
    (proc/str(pid)).mkdir(parents=True)
    (proc/str(pid)/'cgroup').write_text('9:memory:/slurm/job_7/step_0\n')
    (proc/'mounts').write_text(f'none {mount} cgroup rw,memory 0 0\n')
    (step/'memory.limit_in_bytes').write_text(str(2**61))
    (step/'memory.usage_in_bytes').write_text('1')
    (job/'memory.limit_in_bytes').write_text(str(16*2**30))
    (job/'memory.usage_in_bytes').write_text(str(5*2**30))
    assert cgroup_memory_headroom_bytes(pid,proc_root=proc)==11*2**30

def test_allocated_gpu_telemetry_parser_rejects_malformed_rows():
    row='GPU-123, RTX A6000, 595.71.05, 85, 61, 10948, 49140, 192.4, 67'
    parsed=parse_gpu_row(row)
    assert parsed['gpu_uuid']=='GPU-123' and parsed['gpu_utilization_percent']==85
    assert parsed['gpu_device_memory_total_gib']==pytest.approx(49140/1024)
    with pytest.raises(ValueError):
        parse_gpu_row('GPU-123, RTX A6000, 595.71.05, N/A, 61, 1, 2, 3, 4')

def test_allocated_gpu_selector_uses_container_logical_zero_not_physical_slurm_id(monkeypatch):
    # Slurm's physical ID can differ from the one-GPU namespace exposed by
    # Apptainer.  The worker itself is always cuda:0, so telemetry must be too.
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','0')
    monkeypatch.setenv('SLURM_STEP_GPUS','6')
    assert allocated_gpu_selector()=='0'
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','0,1')
    with pytest.raises(ValueError,match='ambiguous'):
        allocated_gpu_selector()
