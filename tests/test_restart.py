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
