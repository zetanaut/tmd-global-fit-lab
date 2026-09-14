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
from tmdlab.contracts import FEASIBILITY_DIAGNOSTICS

def execute(tmp_path,monkeypatch,*,forward_limit=600,steps=0,resume_arrays=None,fail_prepare=False,
            diagnostics=False,policy='p1-resume-v1',deadline_seconds=300):
    t=read(Path(__file__).parents[1]/"trials/replay-w8-cpu-a01.json")
    t["budget"]["forwards"]=forward_limit
    if steps:
        t.update(kind='continuation',phase='P1',phases=[dict(mu=1e-6,updates=steps)],
            continuation_binding=dict(start_checkpoint_sha256='0'*64,start_q_per_measurement=1.,
                accepted_updates_before=160,optimizer_history_reset=True,allocation_id='p1-test-lifecycle',
                budget_origin='new_allocation',prior_phase='P0'))
    if resume_arrays is not None:
        prior=int(resume_arrays['counters'][2])
        t.update(execution_policy=policy,start_checkpoint='restart:'+'0'*64,
            restart_binding=dict(parent_run_id='synthetic-parent',state_sha256='0'*64,
                accepted_updates_before=prior,optimizer_history_reset=False),
            trajectory_budget=dict(accepted_updates=prior+steps,forwards=1000,full_calls=300,model_seconds=21600),
            optimizer=dict(line_search='unit-backtracking'))
        t['budget']['endpoint_reserve_seconds']=120
        if policy in ('p1-time-window-v1','p1-time-window-v2'):
            t['budget'].update(segment_seconds=7200,total_seconds=7800,
                accepted_updates=max(t['budget']['accepted_updates'],steps),
                forwards=16384,full_calls=8192)
            t['trajectory_budget'].update(forwards=32768,full_calls=16384)
            t['decision_record']='decisions/synthetic-time-window-test.md'
            if policy=='p1-time-window-v2':
                t['budget'].update(segment_seconds=25200,total_seconds=26400,
                    endpoint_reserve_seconds=300)
    if diagnostics:t['diagnostics']=dict(FEASIBILITY_DIAGNOSTICS)
    path=tmp_path/"trial.json";write(path,t)
    now=time.monotonic()
    write(tmp_path/"launch.json",dict(trial_sha256=sha(path),model_deadline_monotonic=now+deadline_seconds,t0_monotonic=now))
    initial=flat(build())
    def values(theta):return np.full(2290,1.+.001*theta[0])
    class Bundle:
        def __init__(self,path):self.index={"identity":t["bundle_identity"]}
        def checkpoint(self,name):
            return dict(model=t["model"],parameter_schema=schema(build()),q_per_measurement=float(np.mean((2-values(initial))**2))),dict(theta=initial,values=values(initial))
    class Metric:
        def __init__(self,b):
            self.sigma=np.ones(2290);self.info=dict(ids=[f'synthetic-{i}' for i in range(2290)])
        def describe(self,v):
            return dict(q_per_measurement=float(np.mean((2-v)**2)),min_T_over_sigma=float(v.min()))
        def score(self,v,mu):
            s=v-1e-8
            if not (s>0).all():return None
            q=float(np.mean((2-v)**2));barrier=float(-mu*np.mean(np.log(s)))
            raw=-(2-v)/2290
            return dict(values=v.copy(),q_per_measurement=q,objective=q/2+barrier,barrier=barrier,cotangent=raw-mu/(2290*s),raw_cotangent=raw,min_T_over_sigma=float(v.min()))
    class Engine:
        closed=False;cache_bytes=0;groups=[]
        def __init__(self,*args,**kwargs):
            if fail_prepare:raise RuntimeError('synthetic preparation failure')
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
    assert Engine.closed is not fail_prepare
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

def test_sigterm_from_another_thread_is_deferred_until_commit():
    import os
    import threading
    gate=worker.DeferredTermination(); old=signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM,gate.handle)
    completed=[]
    try:
        with pytest.raises(worker.Stop):
            with gate.transaction():
                sender=threading.Thread(target=lambda:os.kill(os.getpid(),signal.SIGTERM))
                sender.start(); sender.join(timeout=1)
                assert not sender.is_alive()
                assert gate.pending
                completed.append('coherent snapshot')
        assert completed==['coherent snapshot']
    finally:signal.signal(signal.SIGTERM,old)

def test_resume_preparation_failure_retains_parent_and_zero_new_dispatch_ledger(tmp_path,monkeypatch):
    first=tmp_path/'first'; failed=tmp_path/'failed'; first.mkdir(); failed.mkdir()
    execute(first,monkeypatch,steps=3)
    with np.load(first/'restart.npz',allow_pickle=False) as z:saved={k:z[k].copy() for k in z.files}
    code,summary=execute(failed,monkeypatch,steps=3,resume_arrays=saved,fail_prepare=True)
    assert code==2 and summary['status']=='failed'
    ledger=read(failed/'counters.json')
    assert ledger['forwards']==0 and ledger['call_in_flight'] is False
    assert ledger['trajectory_counters']['forwards']==saved['counters'][0]
    with np.load(failed/'restart.npz',allow_pickle=False) as z:
        assert all(np.array_equal(z[k],saved[k]) for k in z.files)

@pytest.mark.parametrize('policy',['p1-time-window-v1','p1-time-window-v2'])
def test_passive_diagnostics_preserve_trajectory_and_all_model_call_counts(tmp_path,monkeypatch,policy):
    import json
    parent=tmp_path/'parent';control=tmp_path/'control';observed=tmp_path/'observed'
    for path in (parent,control,observed):path.mkdir()
    execute(parent,monkeypatch,steps=3)
    with np.load(parent/'restart.npz',allow_pickle=False) as z:saved={k:z[k].copy() for k in z.files}
    _,baseline=execute(control,monkeypatch,steps=6,resume_arrays=saved)
    code,recorded=execute(observed,monkeypatch,steps=6,resume_arrays=saved,
        policy=policy,diagnostics=True,deadline_seconds=600)
    assert code==0 and recorded['counters']==baseline['counters']
    assert recorded['trajectory_counters']==baseline['trajectory_counters']
    for name in ('last.npz','restart.npz'):
        with np.load(control/name,allow_pickle=False) as a,np.load(observed/name,allow_pickle=False) as b:
            assert a.files==b.files
            assert all(np.array_equal(a[k],b[k]) for k in a.files)
    events=[json.loads(line) for line in (observed/'line-search.ndjson').read_text().splitlines()]
    assert sum(e['verdict']=='armijo_passed' for e in events)==6
    report=read(observed/'diagnostic-summary.json')
    assert report['model_calls']==0 and report['segment_counters']==recorded['counters']
    assert report['trajectory_counters']==recorded['trajectory_counters']

@pytest.mark.parametrize('policy',['p1-time-window-v1','p1-time-window-v2'])
def test_32_update_review_does_not_end_the_time_window(tmp_path,monkeypatch,policy):
    parent=tmp_path/'parent';observed=tmp_path/'observed';parent.mkdir();observed.mkdir()
    execute(parent,monkeypatch,steps=3)
    with np.load(parent/'restart.npz',allow_pickle=False) as z:saved={k:z[k].copy() for k in z.files}
    # Keep this synthetic trajectory outside the convergence gate so the test
    # isolates the checkpoint cadence from convergence-based early stopping.
    monkeypatch.setattr(worker,'plateau',lambda *args:dict(eligible=True,passed=False))
    code,summary=execute(observed,monkeypatch,steps=97,resume_arrays=saved,
        policy=policy,diagnostics=True,deadline_seconds=600)
    assert code==0 and summary['counters']['accepted_updates']==97
    report=read(observed/'diagnostic-review-0032.json')
    assert report['segment_counters']['accepted_updates']==32
    assert report['trajectory_counters']['accepted_updates']==35
    assert read(observed/'diagnostic-summary.json')['review_files']==[
        'diagnostic-review-0032.json','diagnostic-review-0064.json','diagnostic-review-0096.json']

@pytest.mark.parametrize('policy',['p1-time-window-v1','p1-time-window-v2'])
def test_time_reserve_ends_optimization_and_keeps_raw_endpoint_gradient(tmp_path,monkeypatch,policy):
    parent=tmp_path/'parent';observed=tmp_path/'observed';parent.mkdir();observed.mkdir()
    execute(parent,monkeypatch,steps=3)
    with np.load(parent/'restart.npz',allow_pickle=False) as z:saved={k:z[k].copy() for k in z.files}
    code,summary=execute(observed,monkeypatch,steps=33,resume_arrays=saved,
        policy=policy,diagnostics=True,deadline_seconds=120)
    assert code==2 and summary['status']=='partial'
    assert summary['optimization_budget_stop']=='endpoint_time_reserve'
    assert summary['counters']['accepted_updates']==0
    assert not summary['plateau']['passed']
    with np.load(observed/'last.npz',allow_pickle=False) as z:assert 'raw_gradient' in z.files
