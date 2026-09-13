"""Frozen paired line-search decision; no model calls or plotting inference."""
from pathlib import Path
import numpy as np
from .io import read,sha,within,digest
from .results import validate_record

RESTART='restart:22f93b2263cf2494d1fc5e40a70f15f82ffed173c0f0bec76e86e97735972dff'

def origin(trial,root):
    """Verify calibration identity through any interrupted native segments."""
    start=trial['start_checkpoint']; seen=set()
    while start!=RESTART:
        if not start.startswith('restart:') or start in seen:
            raise ValueError('calibration is not a descendant of its fixed parent')
        seen.add(start)
        m=read(within(root,'restarts/'+start[8:]+'.json'))
        if m['identity']!=start[8:] or digest({k:v for k,v in m.items() if k!='identity'})!=start[8:]:
            raise ValueError('calibration restart identity mismatch')
        path=within(root,m['parent_record']['path'])
        if sha(path)!=m['parent_record']['sha256']:raise ValueError('calibration ancestor hash mismatch')
        record=validate_record(read(path)); spec=within(root,'trials/'+record['trial_id']+'.json')
        if sha(spec)!=record['trial_sha256']:raise ValueError('calibration ancestor spec mismatch')
        prior=read(spec)
        for key in ('seed','model','bundle_identity','source_identity','metric_identity','optimizer','trajectory_budget'):
            if prior[key]!=trial[key]:raise ValueError('calibration branch changed protocol: '+key)
        start=prior['start_checkpoint']
    return start

def evidence(run,record_path,*,root=None):
    root=Path(__file__).resolve().parents[1] if root is None else Path(root)
    run=Path(run); record=validate_record(read(record_path))
    launch=read(run/'launch.json'); trial=read(run/'trial.json')
    spec=within(root,'trials/'+record['trial_id']+'.json')
    if (record['run_id']!=launch['run_id'] or sha(spec)!=record['trial_sha256']
        or launch['trial_sha256']!=record['trial_sha256'] or read(spec)!=trial):
        raise ValueError('calibration run/spec mismatch')
    if 'trial.json' not in record['files']:raise ValueError('missing published runtime trial bytes')
    for name,item in record['files'].items():
        path=within(run,name)
        if sha(path)!=item['sha256'] or path.stat().st_size!=item['bytes']:
            raise ValueError('calibration published file mismatch: '+name)
    ready=(record['status']=='completed' and record['audit']['passed']
        and record.get('trajectory_counters',{}).get('accepted_updates')==30
        and record['audit'].get('raw_gradient_max') is not None
        and read(run/'preflight.json').get('passed'))
    last=max(run.glob('accepted-*.json'),default=None)
    step=read(last) if last is not None else {}
    if ready and step.get('trajectory_counters',{}).get('accepted_updates')!=30:
        raise ValueError('calibration endpoint accepted-step mismatch')
    if ready and abs(step['q_per_measurement']-record['audit']['q_per_measurement'])>1e-10:
        raise ValueError('calibration accepted score/audit mismatch')
    counts=record.get('trajectory_counters') or {}
    return dict(run_id=record['run_id'],result_identity=record['identity'],
        policy=trial['optimizer']['line_search'],start=origin(trial,root),
        comparable=bool(ready),q=record['audit'].get('q_per_measurement') if record['audit'] else None,
        objective=step.get('objective'),new_forwards=counts.get('forwards',201)-201,
        seed=trial['seed'],model=trial['model'],bundle=trial['bundle_identity'],
        metric=trial['metric_identity'],source=trial['source_identity'])

def decide(control,adaptive):
    if control['policy']!='unit-backtracking' or adaptive['policy']!='previous-alpha-double':
        raise ValueError('wrong calibration arms')
    if control['start']!=RESTART or adaptive['start']!=RESTART:
        raise ValueError('calibration needs the fixed common parent')
    for key in ('seed','model','bundle','metric','source'):
        if control[key]!=adaptive[key]:raise ValueError('unpaired calibration: '+key)
    result=dict(schema='tmd-p1-optimizer-calibration-decision-v1',control=control,adaptive=adaptive,
        thresholds=dict(max_q_disadvantage=1e-4,max_objective_disadvantage=5e-5,min_forward_saving_fraction=.25),
        architecture_selected=False,production_selected=False)
    if not control['comparable'] or not adaptive['comparable']:
        return dict(result,status='incomplete-common-milestone',selected_policy=None)
    for arm in (control,adaptive):
        if not all(np.isfinite(arm[k]) for k in ('q','objective','new_forwards')) or arm['new_forwards']<=0:
            raise ValueError('invalid paired decision metrics')
    tests=dict(q_noninferior=adaptive['q']<=control['q']+1e-4,
        objective_noninferior=adaptive['objective']<=control['objective']+5e-5,
        forward_saving=adaptive['new_forwards']<=.75*control['new_forwards'])
    return dict(result,status='comparable',tests=tests,
        selected_policy='previous-alpha-double' if all(tests.values()) else 'unit-backtracking')
