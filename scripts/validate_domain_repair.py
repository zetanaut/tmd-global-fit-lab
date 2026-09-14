#!/usr/bin/env python3
"""Bounded CPU engineering proof; no full-data forward/VJP or fit updates.

Compare the repaired finite algebra with the pinned historical implementation,
reproduce the first-boundary underflow, verify inputs and the exact retry ledger.
The small synthetic contractions are explicitly not scientific trial results.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import types

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from torch.nn import functional as F
from tmdlab.bundle import Bundle
from tmdlab.contracts import validate_trial
from tmdlab.domain import NumericalDomainError
from tmdlab.engine import Engine
from tmdlab.io import read, write, sha, utc
from tmdlab.lbfgs import two_loop
from tmdlab.metric import Metric
from tmdlab.models import build, put
from tmdlab.restart import load_restart, elapsed_before, segment_allowance, curvature_certificate


def old_module(commit, name):
    raw=subprocess.check_output(['git','show',f'{commit}:tmdlab/{name}.py'])
    module=types.ModuleType(f'tmdlab._domain_baseline_{name}')
    sys.modules[module.__name__]=module
    exec(compile(raw,f'{commit}:tmdlab/{name}.py','exec'),module.__dict__)
    return module, hashlib.sha256(raw).hexdigest()


def tiny_engine(cls, model):
    engine=cls.__new__(cls)
    engine.device=torch.device('cpu');engine.model=model;engine.indices=[0,1];engine.signatures={}
    def f(value):return torch.tensor(value,dtype=torch.float64)
    def i(value):return torch.tensor(value,dtype=torch.int64)
    engine.groups=[]
    for index,process,species in ((0,'DY',1),(1,'SIDIS',21)):
        engine.groups.append(dict(indices=[index],process=process,
            c1=f([[1.,.2]]),c2=f([[1.,.3]]),cp=f([[1.,4.]]),
            s1=i([0]),s2=i([species]),i1=i([0]),i2=i([0]),ip=i([0]),
            weights=f([[.7]]),fixed=f([.1]),denominator=f([2.]),volume=f([.9])))
    return engine


def main(args):
    if not re.fullmatch('[0-9a-f]{40}',args.baseline):raise ValueError('exact historical commit required')
    if args.out.exists():raise ValueError('validation receipt already exists')
    torch.set_num_threads(1)
    root=Path.cwd();trial=validate_trial(read(args.trial))
    bundle=Bundle(args.bundle,verify_all=True)
    manifest,state=load_restart(root,trial['start_checkpoint'][8:],trial,bundle)
    before=elapsed_before(root,manifest)
    assert before==manifest['model_seconds_before']
    assert segment_allowance(trial,before)==4993
    with np.load(args.run/'restart.npz',allow_pickle=False) as z:
        for key in z.files:
            if key!='counters':assert np.array_equal(state[key],z[key])
        assert state['counters'][0]==int(z['counters'][0])+1
    old_models,models_sha=old_module(args.baseline,'models')
    old_engine,engine_sha=old_module(args.baseline,'engine')
    old_metric,metric_sha=old_module(args.baseline,'metric')
    old_engine.put=old_models.put
    metric=Metric(bundle);prior_metric=old_metric.Metric.__new__(old_metric.Metric)
    prior_metric.__dict__.update(metric.__dict__)
    comparisons=[]
    for name in ('initial.npz','checkpoint-073.npz','checkpoint-075.npz'):
        with np.load(args.run/name,allow_pickle=False) as z:
            theta=z['theta'].copy();values=z['values'].copy()
        expected=prior_metric.score(values,1e-6);actual=metric.score(values,1e-6)
        assert expected.keys()==actual.keys()
        assert all(np.array_equal(expected[key],actual[key]) for key in expected)
        engines=(tiny_engine(old_engine.Engine,old_models.build()),tiny_engine(Engine,build()))
        outputs=[engine.evaluate(theta,np.array([.3,-.2])) for engine in engines]
        assert all(np.array_equal(a,b) for a,b in zip(*outputs))
        comparisons.append(dict(checkpoint=name,sha256=sha(args.run/name),
            all_metric_fields_bit_identical=True,synthetic_predictions_and_vjp_bit_identical=True))
    direction=-two_loop(state['penalized_gradient'],list(zip(state['history_s'],state['history_y'],state['history_rho'])))
    metadata,operator=bundle.operator(0)
    keys=np.unique(operator['point_index']*10+operator['species1'])
    coordinates=operator['coordinates'][keys//10,:2]
    b=torch.as_tensor(coordinates[:,0]);x=torch.as_tensor(coordinates[:,1])
    species=torch.as_tensor(keys%10,dtype=torch.int64);model=build();probes=[]
    with torch.no_grad():
        for alpha in (0.,1.,.5,.25,.125):
            put(model,state['theta']+alpha*direction);boundary=model.incoming
            c=boundary.condition(torch.cat([torch.stack((2*x-1,torch.log(x),torch.log1p(-x)),dim=-1),boundary.flavor(species)],dim=-1))
            logits=boundary.raw_widths[species]+boundary.delta_width_head(c).squeeze(-1)
            damping=F.softplus(logits)
            try:boundary.log_multiplier(b,x,species);verdict='boundary_valid'
            except NumericalDomainError as exc:verdict=exc.code
            probes.append(dict(alpha=alpha,min_logit=float(logits.min()),max_logit=float(logits.max()),
                zero_damping_nodes=int((damping==0).sum()),finite_logits=bool(torch.isfinite(logits).all()),verdict=verdict))
    assert [p['verdict'] for p in probes]==['boundary_valid','boundary_zero_damping','boundary_zero_damping','boundary_valid','boundary_valid']
    record=dict(schema='tmd-domain-repair-engineering-v1',generated_utc=utc(),passed=True,
        baseline_code_commit=args.baseline,baseline_file_sha256=dict(models=models_sha,engine=engine_sha,metric=metric_sha),
        current_file_sha256={name:sha(root/'tmdlab'/f'{name}.py') for name in ('models','engine','metric','worker','domain','diagnostics','contracts','restart')},
        trial_sha256=sha(args.trial),restart_identity=manifest['identity'],input_identity=bundle.index['identity'],
        verified_input_files=len(bundle.index['files']),model_seconds_before=before,effective_model_seconds=4993,
        restored_counters=manifest['counters'],optimizer_arrays_bit_identical=True,failed_final_dispatch_retained=True,
        finite_equivalence=comparisons,synthetic_engine_evaluations=6,synthetic_rows_per_evaluation=2,
        full_data_forward_vjp_calls=0,optimizer_updates=0,boundary_check_calls=5,boundary_condition_probe_calls=5,
        boundary_probe_observation=metadata['row']['observation_id'],boundary_probe_nodes=len(keys),
        direction_l2=float(np.linalg.norm(direction)),g_dot_direction=float(state['penalized_gradient']@direction),
        curvature_certificates=[curvature_certificate(s,y,rho) for s,y,rho in zip(state['history_s'],state['history_y'],state['history_rho'])],
        boundary_probes=probes,full_observable_feasibility_at_smaller_alpha='not_established_by_this_engineering_probe')
    write(args.out,record);print(args.out)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',required=True)
    for name in ('run','bundle','trial','out'):parser.add_argument('--'+name,type=Path,required=True)
    main(parser.parse_args())
