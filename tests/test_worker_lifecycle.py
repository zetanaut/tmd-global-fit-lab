"""Synthetic engineering fixtures only; never added to scientific result records."""
from pathlib import Path
from types import SimpleNamespace
import signal
import time
import numpy as np
import pytest
from tmdlab import worker
from tmdlab.io import read,write,sha
from tmdlab.models import build,flat,schema

def execute(tmp_path,monkeypatch,*,forward_limit=600,steps=0,resume_arrays=None):
    t=read(Path(__file__).parents[1]/"trials/replay-w8-cpu-a01.json")
    t["budget"]["forwards"]=forward_limit
    if steps:
        t.update(kind='continuation',phase='P1',phases=[dict(mu=1e-6,updates=steps)],
            continuation_binding=dict(start_checkpoint_sha256='0'*64,start_q_per_measurement=1.,
                accepted_updates_before=160,optimizer_history_reset=True,allocation_id='p1-test-lifecycle',
                budget_origin='new_allocation',prior_phase='P0'))
    if resume_arrays is not None:
        prior=int(resume_arrays['counters'][2])
        t.update(execution_policy='p1-resume-v1',start_checkpoint='restart:'+'0'*64,
            restart_binding=dict(parent_run_id='synthetic-parent',state_sha256='0'*64,
                accepted_updates_before=prior,optimizer_history_reset=False),
            trajectory_budget=dict(accepted_updates=prior+steps,forwards=1000,full_calls=300),
            optimizer=dict(line_search='unit-backtracking'))
        t['budget']['endpoint_reserve_seconds']=120
    path=tmp_path/"trial.json";write(path,t)
    now=time.monotonic()
    write(tmp_path/"launch.json",dict(trial_sha256=sha(path),model_deadline_monotonic=now+300,t0_monotonic=now))
    initial=flat(build())
    def values(theta):return np.full(2290,1.+.001*theta[0])
    class Bundle:
        def __init__(self,path):self.index={"identity":t["bundle_identity"]}
        def checkpoint(self,name):
            return dict(model=t["model"],parameter_schema=schema(build()),q_per_measurement=float(np.mean((2-values(initial))**2))),dict(theta=initial,values=values(initial))
    class Metric:
        def __init__(self,b):self.sigma=np.ones(2290)
        def score(self,v,mu):
            s=v-1e-8
            if not (s>0).all():return None
            q=float(np.mean((2-v)**2));barrier=float(-mu*np.mean(np.log(s)))
            raw=-(2-v)/2290
            return dict(values=v.copy(),q_per_measurement=q,objective=q/2+barrier,barrier=barrier,cotangent=raw-mu/(2290*s),raw_cotangent=raw,min_T_over_sigma=float(v.min()))
    class Engine:
        closed=False;cache_bytes=0;groups=[]
        def __init__(self,*args,**kwargs):pass
        def evaluate(self,theta,cot=None,**kwargs):
            g=None
            if cot is not None:g=np.zeros_like(theta);g[0]=.001*np.sum(cot)
            return values(theta),g
        def close(self):Engine.closed=True
    monkeypatch.setattr(worker,"Bundle",Bundle);monkeypatch.setattr(worker,"Metric",Metric);monkeypatch.setattr(worker,"Engine",Engine)
    if resume_arrays is not None:
        def restart(*_):
            return dict(model=t['model'],parameter_schema=schema(build()),
                q_per_measurement=float(np.mean((2-resume_arrays['values'])**2))),resume_arrays
        monkeypatch.setattr(worker,'load_restart',restart)
    old=signal.getsignal(signal.SIGTERM)
    try:code=worker.run(SimpleNamespace(trial=path,out=tmp_path,bundle=tmp_path,device="cpu"))
    finally:signal.signal(signal.SIGTERM,old)
    assert Engine.closed
    return code,read(tmp_path/"worker-summary.json")

def test_replay_worker_complete_lifecycle(tmp_path,monkeypatch):
    code,summary=execute(tmp_path,monkeypatch)
    assert code==0 and summary["status"]=="completed"
    assert summary["counters"]["accepted_updates"]==0
    assert summary["preflight"]["passed"]
    assert len(summary["preflight"]["directional"])==2
    with np.load(tmp_path/"last.npz",allow_pickle=False) as z:
        assert "raw_gradient" in z.files and z["values"].shape==(2290,)

def test_budget_stop_is_partial_not_converged(tmp_path,monkeypatch):
    code,summary=execute(tmp_path,monkeypatch,forward_limit=1)
    assert code==2 and summary["status"]=="partial"
    assert summary["stop_reason"]=="call_budget"
    assert summary["counters"]["forwards"]==1
    assert not summary["preflight"].get("passed",False)

def test_real_worker_split_resume_preserves_next_steps_and_charges_preflight(tmp_path,monkeypatch):
    import numpy as np
    whole=tmp_path/'whole'; first=tmp_path/'first'; second=tmp_path/'second'
    for path in (whole,first,second):path.mkdir()
    code,expected=execute(whole,monkeypatch,steps=6)
    assert code==0
    code,partial=execute(first,monkeypatch,steps=3)
    assert code==0
    with np.load(first/'restart.npz',allow_pickle=False) as z: saved={k:z[k].copy() for k in z.files}
    code,resumed=execute(second,monkeypatch,steps=3,resume_arrays=saved)
    assert code==0 and resumed['optimizer_history_reset'] is False
    assert resumed['trajectory_counters']['accepted_updates']==6
    assert resumed['trajectory_counters']['forwards']>expected['counters']['forwards']
    with np.load(whole/'last.npz',allow_pickle=False) as w,np.load(second/'last.npz',allow_pickle=False) as s:
        assert np.array_equal(w['theta'],s['theta'])
        assert np.array_equal(w['penalized_gradient'],s['penalized_gradient'])
    with np.load(whole/'restart.npz',allow_pickle=False) as w,np.load(second/'restart.npz',allow_pickle=False) as s:
        assert np.array_equal(w['history_s'],s['history_s'])
        assert np.array_equal(w['state_values'],s['state_values'])
