"""Synthetic /proc/cgroup fixtures; no allocation, CUDA, or scientific work."""
import json
import time
from types import SimpleNamespace

import pytest

from tmdlab import run

GIB=2**30

class Cgroups:
    pid=4242
    def __init__(self,tmp,version=1):
        self.proc=tmp/'proc'; self.mount=tmp/'memory'
        self.job=self.mount/'slurm/job_7'; self.step=self.job/'step_0'
        self.step.mkdir(parents=True); (self.proc/str(self.pid)).mkdir(parents=True)
        self.version=version
        self.limit='memory.limit_in_bytes' if version==1 else 'memory.max'
        self.usage='memory.usage_in_bytes' if version==1 else 'memory.current'
        kind='cgroup rw,memory' if version==1 else 'cgroup2 rw'
        (self.proc/'mounts').write_text(f'none {self.mount} {kind} 0 0\n')
        self.membership('/slurm/job_7/step_0'); self.identity()
        self.cap(self.mount,2**61,0); self.cap(self.job,16*GIB,3*GIB)
        self.cap(self.step,12*GIB,2*GIB)

    def membership(self,path):
        prefix='9:memory:' if self.version==1 else '0::'
        (self.proc/str(self.pid)/'cgroup').write_text(prefix+path+'\n')

    def identity(self,flags=0,start=123):
        fields=['S']+['0']*19
        fields[6]=str(flags); fields[19]=str(start)
        (self.proc/str(self.pid)/'stat').write_text(
            f'{self.pid} (worker with ) spaces) '+ ' '.join(fields)+'\n')

    def cap(self,path,limit,usage):
        (path/self.limit).write_text(str(limit)); (path/self.usage).write_text(str(usage))

    def bind(self): return run.CgroupMemoryBinding(self.pid,proc_root=self.proc)

@pytest.mark.parametrize('version',[1,2])
def test_binding_keeps_stricter_child_and_ancestor_and_reads_fresh_usage(tmp_path,version):
    cg=Cgroups(tmp_path,version); bound=cg.bind()
    assert bound.read()==10*GIB  # Child cap is stricter than the job cap.
    cg.cap(cg.job,16*GIB,9*GIB)
    assert bound.read()==7*GIB   # Fresh stricter parent usage, not cached headroom.
    cg.cap(cg.step,9*GIB,4*GIB)
    assert bound.read()==5*GIB   # Fresh changed limit as well as changed usage.

def test_v1_pre_reap_transition_keeps_fresh_bound_scope(tmp_path):
    cg=Cgroups(tmp_path); bound=cg.bind()
    cg.membership('/'); cg.identity(flags=4)
    with pytest.raises(ValueError,match='finite cgroup'):
        run.cgroup_memory_headroom_bytes(cg.pid,proc_root=cg.proc)
    cg.cap(cg.step,12*GIB,3*GIB)
    assert bound.read()==9*GIB and bound.exit_transition
    cg.cap(cg.step,12*GIB,5*GIB)
    assert bound.read()==7*GIB  # Exit transition cannot freeze a healthy value.

@pytest.mark.parametrize('flags,path',[(0,'/'),(0,'/slurm/job_7/step_0/stricter'),
    (4,'/slurm/job_7/step_0/stricter')])
def test_live_or_nonroot_migration_fails_closed(tmp_path,flags,path):
    cg=Cgroups(tmp_path); bound=cg.bind()
    cg.membership(path); cg.identity(flags=flags)
    with pytest.raises(ValueError,match='migration'): bound.read()

def test_v2_root_transition_is_not_a_v1_exit_exception(tmp_path):
    cg=Cgroups(tmp_path,2); bound=cg.bind()
    cg.membership('/'); cg.identity(flags=4)
    with pytest.raises(ValueError,match='migration'): bound.read()

@pytest.mark.parametrize('exiting',[False,True])
@pytest.mark.parametrize('target',['step','job'])
@pytest.mark.parametrize('loss',['missing','unlimited'])
def test_any_initial_finite_cap_loss_fails_even_when_other_cap_survives(tmp_path,exiting,target,loss):
    cg=Cgroups(tmp_path); bound=cg.bind()
    if exiting: cg.membership('/'); cg.identity(flags=4)
    path=getattr(cg,target)
    if loss=='missing': (path/cg.limit).unlink()
    else: (path/cg.limit).write_text(str(2**61))
    with pytest.raises(ValueError,match='finite cgroup'): bound.read()

def test_scope_replacement_and_pid_reuse_fail_closed(tmp_path):
    cg=Cgroups(tmp_path); bound=cg.bind()
    cg.identity(start=456)
    with pytest.raises(ValueError,match='identity changed'): bound.read()
    cg.identity()
    cg.step.rename(cg.job/'old_step'); cg.step.mkdir()
    cg.cap(cg.step,12*GIB,2*GIB)
    with pytest.raises(ValueError,match='replaced'): bound.read()

def test_cannot_bind_after_worker_already_entered_exit(tmp_path):
    cg=Cgroups(tmp_path); cg.identity(flags=4)
    with pytest.raises(ValueError,match='already exiting'): cg.bind()

def test_builtin_sampler_survives_pre_reap_transition_without_poll_grace(tmp_path,monkeypatch):
    cg=Cgroups(tmp_path/'fixture')
    original=run.CgroupMemoryBinding
    monkeypatch.setattr(run,'CgroupMemoryBinding',lambda pid:original(pid,proc_root=cg.proc))
    class Owned:
        pid=cg.pid; code=None; calls=0
        def poll(self): return self.code
        def wait(self,timeout=None): assert self.code is not None; return self.code
    owned=Owned()
    # The actual builtin sample() runs, including scope verification. Only OS
    # process memory is synthetic. On sample 2 cgroup has changed but poll is
    # still None; sample 3 exits after proving sample 2 was durably consumed.
    class Process:
        def __init__(self,pid): self.pid=pid
        def children(self,recursive): return []
        def is_running(self): return True
        def memory_info(self):
            owned.calls+=1
            if owned.calls==2:
                cg.membership('/'); cg.identity(flags=4)
                cg.cap(cg.step,12*GIB,3*GIB)
                assert owned.poll() is None
            elif owned.calls==3:
                rows=[json.loads(s) for s in (tmp_path/'resources.ndjson').read_text().splitlines()]
                assert any(row['cgroup_worker_exit_transition'] for row in rows)
                owned.code=0
            return SimpleNamespace(rss=GIB)
    monkeypatch.setattr(run.psutil,'Process',Process)
    def unexpected_stop(process): raise AssertionError('healthy owned worker stopped')
    monkeypatch.setattr(run,'stop_owned',unexpected_stop)
    result=run.supervise(owned,deadline=time.monotonic()+3,
        budget=dict(rss_gib=4,host_available_gib=8),gpu=False,out=tmp_path)
    assert result['stop_reason'] is None and result['exit_code']==0
    assert result['peaks']['samples']>=2
    assert result['peaks']['host_available_min_gib']==9

@pytest.mark.parametrize('mode',['missing','low','stale','zero'])
def test_bound_scope_does_not_bypass_supervisor_safety_gates(tmp_path,monkeypatch,mode):
    cg=Cgroups(tmp_path/'fixture'); bound=cg.bind()
    class Owned:
        pid=cg.pid; code=None
        def poll(self): return self.code
        def wait(self,timeout=None): return self.code
    owned=Owned(); stopped=[]
    def stop(process): stopped.append(process); process.code=-15
    monkeypatch.setattr(run,'stop_owned',stop)
    def sampler(pid,gpu):
        if mode=='missing': (cg.step/cg.limit).unlink()
        if mode=='low': cg.cap(cg.step,12*GIB,5*GIB)
        if mode=='zero':
            owned.code=0
            raise ProcessLookupError('worker disappeared before first valid sample')
        return dict(monotonic=time.monotonic()-(2 if mode=='stale' else 0),
            rss_gib=1,host_available_gib=bound.read()/GIB,accepted_updates=0)
    result=run.supervise(owned,deadline=time.monotonic()+3,
        budget=dict(rss_gib=4,host_available_gib=8),gpu=False,out=tmp_path,sampler=sampler)
    reason={'missing':'telemetry_failure','low':'resource_limit',
        'stale':'telemetry_stale_over_1s','zero':'telemetry_missing_no_samples'}[mode]
    assert result['stop_reason'].startswith(reason)
    assert stopped==([] if mode=='zero' else [owned])
