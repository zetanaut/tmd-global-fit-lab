"""Restart must preserve optimization state, history filtering and counted work."""
import numpy as np
import pytest
from tmdlab.restart import pack_state,validate_arrays,unpack_state,update_history,COUNTERS
from tmdlab.lbfgs import two_loop

class QuadraticMetric:
    def score(self,values,mu):
        return dict(values=values.copy(),q_per_measurement=float(values[0]),objective=float(values[0])/2)

def state(theta):
    g=np.array([1.,4.,9.])*theta
    q=float(theta@g)
    return dict(theta=theta.copy(),gradient=g,gradient_max=float(abs(g).max()),
        values=np.full(2290,q),q_per_measurement=q,mu=1e-6)

def advance(point,history,states,n):
    for _ in range(n):
        new=state(point['theta']-.08*two_loop(point['gradient'],history))
        history=update_history(history,point['theta'],point['gradient'],new['theta'],new['gradient'])
        point=new; states.append(dict(point)); states=states[-21:]
    return point,history,states

def test_split_restart_matches_uninterrupted_optimizer_and_window(tmp_path):
    initial=state(np.array([2.,3.,4.])); counts={k:0 for k in COUNTERS}
    expected,eh,es=advance(initial,[],[initial],45)
    point,history,states=advance(initial,[],[initial],23)
    counts.update(accepted_updates=23,forwards=77,full_calls=25,infeasible_trials=8,line_search_rejections=10)
    a=pack_state(point,history,states,counts,mu=1e-6,last_alpha=.08)
    path=tmp_path/'restart.npz'; np.savez_compressed(path,**a)
    with np.load(path,allow_pickle=False) as z: restored=validate_arrays({k:z[k] for k in z.files},3)
    point,history,states,restored_counts=unpack_state(restored,QuadraticMetric())
    assert restored_counts==counts
    actual,ah,astates=advance(point,history,states,22)
    assert np.array_equal(actual['theta'],expected['theta'])
    assert np.array_equal(actual['gradient'],expected['gradient'])
    assert np.array_equal(two_loop(actual['gradient'],ah),two_loop(expected['gradient'],eh))
    assert np.array_equal([s['values'] for s in astates],[s['values'] for s in es])

def test_restart_rejects_curvature_corruption_and_wrong_endpoint():
    p=state(np.array([1.,2.,3.])); p,h,s=advance(p,[],[p],2)
    a=pack_state(p,h,s,{k:0 for k in COUNTERS},mu=1e-6)
    a['history_rho'][0]*=2
    with pytest.raises(ValueError,match='curvature'): validate_arrays(a,3)
    a=pack_state(p,h,s,{k:0 for k in COUNTERS},mu=1e-6)
    a['values']=a['values']+1
    with pytest.raises(ValueError,match='endpoint'): validate_arrays(a,3)

def test_nonpositive_curvature_is_not_restored_or_appended():
    assert update_history([],np.zeros(3),np.ones(3),np.ones(3),np.zeros(3))==[]

@pytest.mark.parametrize('policy',['p1-resume-v1','p1-resume-v2','p1-time-window-v1'])
def test_kill_between_atomic_restart_and_last_audits_new_state_and_charges_dispatch(tmp_path,policy):
    from tmdlab.audit import endpoint_arrays
    from tmdlab.restart import recover_native
    from tmdlab.io import write,sha
    old=state(np.array([1.,2.,3.])); new,h,s=advance(old,[],[old],1)
    counts=dict.fromkeys(COUNTERS,0); counts.update(accepted_updates=1,forwards=9,full_calls=3)
    a=pack_state(new,h,s,counts,mu=1e-6)
    write(tmp_path/'trial.json',dict(execution_policy=policy))
    np.savez_compressed(tmp_path/'last.npz',theta=old['theta'],values=old['values'],penalized_gradient=old['gradient'])
    np.savez_compressed(tmp_path/'restart.npz',**a)
    path,endpoint=endpoint_arrays(tmp_path)
    assert path.name=='restart.npz' and np.array_equal(endpoint['theta'],new['theta'])
    charged=dict(counts,forwards=10,full_calls=4)
    write(tmp_path/'counters.json',dict(trajectory_counters=charged,call_in_flight=True))
    record=dict(files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in tmp_path.iterdir()},
        audit=dict(passed=True,endpoint_path=path.name,endpoint_sha256=sha(path)))
    recovered=recover_native(tmp_path,record)
    assert dict(zip(COUNTERS,map(int,recovered['counters'])))==charged
    record['audit'].update(endpoint_path='last.npz',endpoint_sha256=sha(tmp_path/'last.npz'))
    with pytest.raises(ValueError,match='differs from audited'):recover_native(tmp_path,record)
    record['audit'].update(endpoint_path=path.name,endpoint_sha256=sha(path))
    record['files'].pop('counters.json')
    with pytest.raises(ValueError,match='terminal dispatch ledger'):recover_native(tmp_path,record)

def test_elapsed_ledger_recovers_legacy_time_and_accumulates_without_reset(tmp_path):
    from tmdlab.io import write,sha,digest
    from tmdlab.restart import elapsed_before,segment_allowance
    def manifest(run,start,elapsed):
        path=tmp_path/(run+'.json')
        write(path,dict(run_id=run,start_checkpoint=start,supervisor=dict(elapsed_seconds=elapsed)))
        m=dict(parent_run_id=run,parent_record=dict(path=path.name,sha256=sha(path)))
        m['identity']=digest(m); write(tmp_path/'restarts'/(m['identity']+'.json'),m)
        return m
    first=manifest('old','overlay:'+'0'*64,1200.)
    second=manifest('new','restart:'+first['identity'],3600.)
    assert elapsed_before(tmp_path,first)==1200.
    assert elapsed_before(tmp_path,second)==4800.
    trial=dict(trajectory_budget=dict(model_seconds=6000),budget=dict(segment_seconds=3600,endpoint_reserve_seconds=120))
    assert segment_allowance(trial,4800.)==1200.
    with pytest.raises(ValueError,match='exhausted'):segment_allowance(trial,5900.)
