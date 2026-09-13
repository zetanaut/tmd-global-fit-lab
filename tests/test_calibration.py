import pytest
from tmdlab.calibration import decide,RESTART,BUNDLE
from tmdlab.io import SOURCE_ID,METRIC_ID

def arms():
    control=dict(policy='unit-backtracking',start=RESTART,comparable=True,q=16.,objective=8.,
        new_forwards=200,seed=2026091208,model=dict(width=8,depth=1),bundle=BUNDLE,
        metric=METRIC_ID,source=SOURCE_ID,hardware_qualified=True)
    return control,dict(control,policy='previous-alpha-double',new_forwards=150)

def test_policy_selected_only_with_progress_and_call_saving():
    c,a=arms(); assert decide(c,a)['selected_policy']=='previous-alpha-double'
    for key,value in (('q',16.001),('objective',8.001),('new_forwards',151)):
        assert decide(c,dict(a,**{key:value}))['selected_policy']=='unit-backtracking'

def test_censored_arms_cannot_select_a_policy():
    c,a=arms()
    for pair in ((dict(c,comparable=False),a),(c,dict(a,comparable=False))):
        result=decide(*pair)
        assert result['selected_policy'] is None and result['status']=='incomplete-common-milestone'

def test_unpaired_or_wrong_parent_comparison_rejected():
    c,a=arms()
    for key,value in (('start','wrong'),('seed',2),('model',dict(width=16,depth=1))):
        with pytest.raises(ValueError):decide(c,dict(a,**{key:value}))

def test_agreeing_arms_still_must_match_fixed_protocol_and_environment():
    c,a=arms()
    for key,value in (('seed',1),('model',dict(width=16,depth=1)),('hardware_qualified',False)):
        with pytest.raises(ValueError):decide(dict(c,**{key:value}),dict(a,**{key:value}))

def test_evidence_binds_registry_bytes_and_semantically_equal_runtime_serialization(tmp_path):
    import json
    from pathlib import Path
    from tmdlab.calibration import evidence
    from tmdlab.io import read,write,sha,digest
    root=Path(__file__).resolve().parents[1]
    record=read(root/'results/continuation-w8-p1-a02/continuation-w8-p1-a02-38d1bf1023dc.json')
    run=tmp_path/'run'; run.mkdir(); registry=tmp_path/'trials'; registry.mkdir()
    trial=dict(trial_id='synthetic-calibration',start_checkpoint=RESTART,
        optimizer=dict(line_search='unit-backtracking'),seed=2026091208,model=dict(width=8,depth=1),
        bundle_identity=record['bundle_identity'],metric_identity=record['metric_identity'],source_identity=record['source_identity'])
    spec=registry/'synthetic-calibration.json'; spec.write_text(json.dumps(trial))
    write(run/'trial.json',trial)
    assert sha(spec)!=sha(run/'trial.json')
    record.update(trial_id=trial['trial_id'],run_id='synthetic-calibration-run',trial_sha256=sha(spec),
        status='completed',worker_status='completed',supervisor=dict(stop_reason=None),
        audit=dict(passed=True,raw_gradient_max=.1,q_per_measurement=16.9),
        trajectory_counters=dict(accepted_updates=30,forwards=401))
    write(run/'launch.json',dict(run_id=record['run_id'],trial_sha256=sha(spec),device='cuda:0'))
    write(run/'environment.json',dict(gpu_name='NVIDIA RTX A6000',dtype='float64',
        deterministic_algorithms=True,TF32=False,torch_threads=1))
    write(run/'preflight.json',dict(passed=True))
    write(run/'accepted-012.json',dict(trajectory_counters=dict(accepted_updates=30),q_per_measurement=16.9,objective=8.45))
    record['files']={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in run.iterdir()}
    record.pop('identity'); record['identity']=digest(record)
    record_path=tmp_path/'record.json'; write(record_path,record)
    result=evidence(run,record_path,root=tmp_path)
    assert result['comparable'] and result['new_forwards']==200 and result['hardware_qualified']
    write(run/'trial.json',dict(trial,seed=2))
    with pytest.raises(ValueError,match='run/spec mismatch'):evidence(run,record_path,root=tmp_path)
