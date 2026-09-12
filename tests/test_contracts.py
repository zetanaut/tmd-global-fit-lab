import copy
import json
from pathlib import Path
import numpy as np
import pytest
import torch
from tmdlab.io import digest,read,within,SOURCE_ID,METRIC_ID
from tmdlab.contracts import validate_trial
from tmdlab.models import Config,build,flat,put
from tmdlab.worker import plateau,two_loop

def example():
    return read(Path(__file__).parents[1]/"trials/replay-w8-cpu-a01.json")

@pytest.mark.parametrize("width,count",[(8,1570),(16,2882),(24,4706)])
def test_exact_parameter_inventory_and_small_b(width,count):
    model=build(Config(width=width))
    assert flat(model).size==count
    assert sum(p.numel() for p in model.cs.parameters())==73
    b=torch.zeros(3,dtype=torch.float64);x=torch.tensor([.1,.3,.8],dtype=torch.float64);species=torch.tensor([0,2,9])
    assert torch.equal(model.incoming.log_multiplier(b,x,species),b)
    assert torch.equal(model.cs(b),b)

def test_parameter_roundtrip_and_reject_bad_schema():
    model=build();theta=flat(model);put(model,theta)
    assert np.array_equal(flat(model),theta)
    with pytest.raises(ValueError):put(model,theta[:-1])
    theta[0]=np.nan
    with pytest.raises(ValueError):put(model,theta)

def test_trial_is_ready_and_replay_cannot_train():
    t=example();validate_trial(t)
    t["phases"]=[{"mu":1e-6,"updates":1}]
    with pytest.raises(ValueError):validate_trial(t)

@pytest.mark.parametrize("key,value",[("forwards",601),("full_calls",241),("segment_seconds",1801),("gpu_gib",21),("rss_gib",49),("cpu_threads",13)])
def test_cap_mutations_rejected(key,value):
    t=example();t["budget"][key]=value
    with pytest.raises(ValueError):validate_trial(t)

@pytest.mark.parametrize("key,value",[("status","draft"),("rows",2289),("dtype","float32"),("metric_identity","x"),("model_family","unverified-new-family")])
def test_identity_mutations_rejected(key,value):
    t=example();t[key]=value
    with pytest.raises(ValueError):validate_trial(t)

def test_two_ten_update_windows_share_boundary():
    states=[dict(mu=1e-6,q_per_measurement=2.,values=np.ones(3),gradient_max=1e-7) for _ in range(21)]
    assert not plateau(states[:20],np.ones(3))["eligible"]
    assert plateau(states,np.ones(3))["passed"]
    states[0]["mu"]=1e-5
    assert not plateau(states,np.ones(3))["passed"]

def test_plateau_rejects_prediction_motion_and_gradient():
    states=[dict(mu=1e-6,q_per_measurement=2.,values=np.ones(3),gradient_max=1e-7) for _ in range(21)]
    states[5]["values"]=np.array([1.,1.,1.02])
    assert not plateau(states,np.ones(3))["passed"]
    states[5]["values"]=np.ones(3);states[-1]["gradient_max"]=1e-3
    assert not plateau(states,np.ones(3))["passed"]

def test_lbfgs_identity_with_empty_history():
    g=np.arange(5,dtype=float)
    assert np.array_equal(two_loop(g,[]),g)

def test_json_duplicates_and_path_escape(tmp_path):
    p=tmp_path/"bad.json";p.write_text('{"x":1,"x":2}')
    with pytest.raises(ValueError):read(p)
    for name in ("../outside","/absolute"):
        with pytest.raises(ValueError):within(tmp_path,name)
    (tmp_path/"link").symlink_to(tmp_path.parent)
    with pytest.raises(ValueError):within(tmp_path,"link/outside")

def test_canonical_digest_independent_of_dictionary_order():
    assert digest({"a":1,"b":2})==digest({"b":2,"a":1})
