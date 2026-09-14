"""Bounded CPU regressions; no scientific model calls or external runs."""
import json
import math
from pathlib import Path
import numpy as np
import pytest
import torch

from tmdlab import worker
from tmdlab.contracts import validate_trial
from tmdlab.domain import CANDIDATE_DOMAIN_POLICY, NumericalDomainError
from tmdlab.engine import Engine
from tmdlab.io import read
from tmdlab.models import build, flat
from test_resume_contracts import time_window
from test_metric import tiny_metric
from test_worker_lifecycle import execute


def parent(tmp_path, monkeypatch):
    path=tmp_path/'parent';path.mkdir()
    code,_=execute(path,monkeypatch,steps=3)
    assert code==0
    with np.load(path/'restart.npz',allow_pickle=False) as z:
        return {k:z[k].copy() for k in z.files}


def resumed(path, monkeypatch, saved, **kwargs):
    path.mkdir()
    return execute(path,monkeypatch,steps=1,resume_arrays=saved,
        diagnostics=True,policy='p1-time-window-v1',
        candidate_errors=CANDIDATE_DOMAIN_POLICY,**kwargs)


def domain_error():
    return NumericalDomainError('boundary_zero_damping','synthetic numerical-domain error')


def test_domain_rejection_requires_exact_opt_in():
    trial=time_window();trial['optimizer']['candidate_errors']=CANDIDATE_DOMAIN_POLICY
    assert validate_trial(trial)
    for policy in ('ignore-all-errors',True,None):
        trial['optimizer']['candidate_errors']=policy
        with pytest.raises(ValueError,match='candidate-domain'):validate_trial(trial)


def test_local_successor_preserves_original_cumulative_allowance_and_spent_costs():
    root=Path(__file__).parents[1]
    trial=validate_trial(read(root/'trials/continuation-w8-feasibility-2h-local-a02.json'))
    parent_trial=read(root/'trials/continuation-w8-feasibility-2h-local-a01.json')
    restart=read(root/'restarts'/f"{trial['start_checkpoint'][8:]}.json")
    record=read(root/restart['parent_record']['path'])
    assert trial['trajectory_budget']==parent_trial['trajectory_budget']
    for key in ('accepted_updates','forwards','full_calls'):
        assert trial['budget'][key]+record['counters'][key]==parent_trial['budget'][key]
        assert restart['counters'][key]+trial['budget'][key]==trial['trajectory_budget'][key]
    elapsed=record['supervisor']['elapsed_seconds']
    assert trial['budget']['segment_seconds']==math.floor(parent_trial['budget']['segment_seconds']-elapsed)==4993
    assert restart['counters']['accepted_updates']==252
    assert restart['counters']['forwards']==2349  # Includes the fatal dispatch.
    assert trial['optimizer']['candidate_errors']==CANDIDATE_DOMAIN_POLICY


def test_domain_rejection_without_error_is_bit_identical(tmp_path,monkeypatch):
    saved=parent(tmp_path,monkeypatch)
    plain=tmp_path/'plain';plain.mkdir()
    _,baseline=execute(plain,monkeypatch,steps=1,resume_arrays=saved,
        diagnostics=True,policy='p1-time-window-v1')
    fixed=tmp_path/'fixed'
    code,result=resumed(fixed,monkeypatch,saved)
    assert code==0 and result['counters']==baseline['counters']
    for name in ('last.npz','restart.npz'):
        with np.load(plain/name,allow_pickle=False) as a,np.load(fixed/name,allow_pickle=False) as b:
            assert a.files==b.files
            assert all(np.array_equal(a[k],b[k]) for k in a.files)


def test_invalid_candidate_backtracks_and_dispatch_stays_charged(tmp_path,monkeypatch):
    saved=parent(tmp_path,monkeypatch)
    def hook(call,theta,cot):
        if call==8:
            assert cot is None
            raise domain_error()
    out=tmp_path/'fixed';code,result=resumed(out,monkeypatch,saved,evaluation_hook=hook)
    assert code==0 and result['counters']['accepted_updates']==1
    assert result['counters']['line_search_rejections']>=1
    assert result['counters']['infeasible_trials']==0
    events=[json.loads(line) for line in (out/'line-search.ndjson').read_text().splitlines()]
    first,second=events[:2]
    assert first['verdict']=='numerical_domain_rejected' and first['alpha']==1.
    assert first['forwards']==8 and first['full_calls']==2
    assert first['domain_error_code']=='boundary_zero_damping'
    assert first['minimum_row_index'] is None and first['violating_row_count'] is None
    assert first['candidate_values_available'] is False
    assert second['attempt']==2 and second['alpha']==.5
    assert read(out/'accepted-001.json')['alpha']==.5
    assert read(out/'diagnostic-summary.json')['candidate_verdicts']['numerical_domain_rejected']==1
    with np.load(out/'last.npz',allow_pickle=False) as z:assert 'raw_gradient' in z.files
    assert read(out/'counters.json')['call_in_flight'] is False


def test_old_policy_does_not_silently_change(tmp_path,monkeypatch):
    saved=parent(tmp_path,monkeypatch);out=tmp_path/'legacy';out.mkdir()
    def hook(call,*_):
        if call==8:raise domain_error()
    code,result=execute(out,monkeypatch,steps=1,resume_arrays=saved,
        diagnostics=True,policy='p1-time-window-v1',evaluation_hook=hook)
    assert code==2 and result['status']=='failed'
    assert result['counters']['accepted_updates']==0
    ledger=read(out/'counters.json')
    assert ledger['call_in_flight'] is False and ledger['forwards']==8
    assert ledger['domain_error_code']=='boundary_zero_damping'


@pytest.mark.parametrize('call_index',[1,2,3,4,9,10])
def test_replay_probe_vjp_and_endpoint_errors_remain_fatal(tmp_path,monkeypatch,call_index):
    saved=parent(tmp_path,monkeypatch)
    def hook(call,*_):
        if call==call_index:raise domain_error()
    out=tmp_path/'fatal';code,result=resumed(out,monkeypatch,saved,evaluation_hook=hook)
    assert code==2 and result['status']=='failed'
    assert 'NumericalDomainError' in result['stop_reason']
    assert result['counters']['line_search_rejections']==0
    assert result['counters']['forwards']==call_index
    # Only the terminal raw-gradient failure occurs after a committed step.
    assert result['counters']['accepted_updates']==(1 if call_index==10 else 0)


@pytest.mark.parametrize('exception',[ValueError,RuntimeError,MemoryError,TimeoutError])
def test_unrelated_candidate_errors_are_never_swallowed(tmp_path,monkeypatch,exception):
    saved=parent(tmp_path,monkeypatch)
    def hook(call,*_):
        if call==8:raise exception('unexpected input/device/deadline failure')
    out=tmp_path/'fatal';code,result=resumed(out,monkeypatch,saved,evaluation_hook=hook)
    assert code==2 and result['status']=='failed'
    assert result['counters']['line_search_rejections']==0
    assert result['counters']['accepted_updates']==0


def test_domain_errors_still_exhaust_the_32_trial_limit(tmp_path,monkeypatch):
    saved=parent(tmp_path,monkeypatch)
    def hook(call,*_):
        if call>=8:raise domain_error()
    out=tmp_path/'exhausted';code,result=resumed(out,monkeypatch,saved,evaluation_hook=hook)
    assert code==2 and result['stop_reason']=='line_search_exhausted_32_trials'
    assert result['counters']['accepted_updates']==0
    assert result['counters']['line_search_rejections']==32
    assert result['counters']['forwards']==39
    assert result['counters']['full_calls']==2
    with np.load(out/'restart.npz',allow_pickle=False) as z:
        for key in ('theta','penalized_gradient','history_s','history_y','state_values'):
            assert np.array_equal(z[key],saved[key])


def test_finite_but_enormous_predictions_are_rejected_before_vjp():
    with pytest.raises(NumericalDomainError) as exc:
        tiny_metric().score(np.full(3,1e200),1e-6)
    assert exc.value.code=='metric_score_nonfinite'


def test_candidate_score_overflow_backtracks_without_a_vjp(tmp_path,monkeypatch):
    saved=parent(tmp_path,monkeypatch)
    def hook(call,*_):
        if call==8:
            original=worker.Metric.score
            def reject_once(self,*args):
                monkeypatch.setattr(worker.Metric,'score',original)
                raise NumericalDomainError('metric_score_nonfinite','synthetic score overflow')
            monkeypatch.setattr(worker.Metric,'score',reject_once)
    out=tmp_path/'overflow';code,result=resumed(out,monkeypatch,saved,evaluation_hook=hook)
    assert code==0 and result['counters']['accepted_updates']==1
    first=json.loads((out/'line-search.ndjson').read_text().splitlines()[0])
    assert first['domain_error_code']=='metric_score_nonfinite'
    assert first['forwards']==8 and first['full_calls']==2
    assert first['candidate_values_available'] is True and first['violating_row_count']==0


def test_real_softplus_underflow_is_typed_without_clipping():
    model=build();b=torch.tensor([1.],dtype=torch.float64)
    x=torch.tensor([.2],dtype=torch.float64);species=torch.tensor([0])
    assert torch.isfinite(model.incoming.log_multiplier(b,x,species)).all()
    with torch.no_grad():model.incoming.raw_widths[0]=-2000.
    with pytest.raises(NumericalDomainError) as exc:model.incoming.log_multiplier(b,x,species)
    assert exc.value.code=='boundary_zero_damping'
    assert model.incoming.raw_widths[0].item()==-2000.
    with pytest.raises(ValueError) as exc:model.incoming.log_multiplier(b,x*0,species)
    assert not isinstance(exc.value,NumericalDomainError)


def tiny_engine():
    engine=Engine.__new__(Engine)
    engine.device=torch.device('cpu');engine.model=build();engine.indices=[0];engine.signatures={}
    def f(value):return torch.tensor(value,dtype=torch.float64)
    def i(value):return torch.tensor(value,dtype=torch.int64)
    engine.groups=[dict(indices=[0],process='DY',c1=f([[1.,.2]]),c2=f([[1.,.3]]),
        cp=f([[1.,9.]]),s1=i([0]),s2=i([1]),i1=i([0]),i2=i([0]),ip=i([0]),
        weights=f([[1.]]),fixed=f([0.]),denominator=f([1.]),volume=f([1.]))]
    return engine


def test_real_product_overflow_is_typed():
    engine=tiny_engine()
    with torch.no_grad():engine.model.cs.network[-1].bias.fill_(2000.)
    with pytest.raises(NumericalDomainError) as exc:engine.evaluate(flat(engine.model))
    assert exc.value.code=='products_nonfinite'


def test_real_vjp_nonfinite_is_not_a_rejectable_domain_error(monkeypatch):
    engine=tiny_engine()
    monkeypatch.setattr(torch.autograd,'grad',lambda output,params,**kw:
        [torch.full_like(p,float('nan')) for p in params])
    with pytest.raises(ValueError) as exc:engine.evaluate(flat(engine.model),np.ones(1))
    assert not isinstance(exc.value,NumericalDomainError)
