from pathlib import Path
import pytest
from tmdlab.io import read
from tmdlab.contracts import validate_trial,FEASIBILITY_DIAGNOSTICS

def resumed():
    t=read(Path(__file__).parents[1]/'trials/continuation-w16-p1-a01.json')
    t.update(execution_policy='p1-resume-v1',start_checkpoint='restart:'+'0'*64,
        restart_binding=dict(parent_run_id='continuation-w16-p1-a01-test',state_sha256='0'*64,
            accepted_updates_before=38,optimizer_history_reset=False),
        trajectory_budget=dict(accepted_updates=96,forwards=4096,full_calls=512,model_seconds=21600),
        optimizer=dict(line_search='unit-backtracking'))
    t['phases'][0]['updates']=58
    t['budget'].update(segment_seconds=13200,total_seconds=13800,forwards=4096,full_calls=512,endpoint_reserve_seconds=120)
    return t

def test_extended_policy_preserves_legacy_ceilings():
    assert validate_trial(resumed())
    t=resumed(); t.pop('execution_policy')
    with pytest.raises(ValueError):validate_trial(t)

def test_p1b_policy_allows_one_new_96_update_segment_but_caps_its_trajectory():
    t=resumed()
    t['execution_policy']='p1-resume-v2'
    t['restart_binding']['accepted_updates_before']=81
    t['phases'][0]['updates']=96
    t['budget']['accepted_updates']=96
    t['trajectory_budget']=dict(accepted_updates=177,forwards=4741,full_calls=612,model_seconds=17696)
    assert validate_trial(t)
    t['trajectory_budget']['accepted_updates']=193
    with pytest.raises(ValueError):validate_trial(t)

def time_window():
    t=resumed();t['execution_policy']='p1-time-window-v1'
    t['restart_binding']['accepted_updates_before']=177
    t['phases'][0]['updates']=4096
    t['budget'].update(accepted_updates=4096,forwards=16384,full_calls=8192,
        segment_seconds=7200,total_seconds=7800,endpoint_reserve_seconds=180)
    t['trajectory_budget']=dict(accepted_updates=4273,forwards=17822,full_calls=8397,model_seconds=13757)
    t['diagnostics']=dict(FEASIBILITY_DIAGNOSTICS)
    t['decision_record']='decisions/synthetic-time-window.md'
    return t

def test_time_window_allows_longer_counts_without_changing_old_policies():
    t=time_window(); assert validate_trial(t)
    for policy in ('p1-resume-v1','p1-resume-v2'):
        t=time_window();t['execution_policy']=policy
        with pytest.raises(ValueError):validate_trial(t)

@pytest.mark.parametrize('damage',['time','updates','forwards','full_calls','diagnostics','cadence','decision','optimizer','trajectory'])
def test_time_window_bounds_and_instrumentation_are_required(damage):
    t=time_window()
    if damage=='time':t['budget']['segment_seconds']=7201
    elif damage in ('updates','forwards','full_calls'):
        key='accepted_updates' if damage=='updates' else damage
        t['budget'][key]+=1
    elif damage=='diagnostics':t.pop('diagnostics')
    elif damage=='cadence':t['diagnostics']['review_interval_updates']=96
    elif damage=='decision':t.pop('decision_record')
    elif damage=='optimizer':t['optimizer']['line_search']='previous-alpha-double'
    elif damage=='trajectory':t['trajectory_budget']['accepted_updates']+=1
    with pytest.raises(ValueError):validate_trial(t)

def long_window():
    t=time_window();t['execution_policy']='p1-time-window-v2'
    t['budget'].update(segment_seconds=25200,total_seconds=26400,endpoint_reserve_seconds=300)
    t['trajectory_budget']['model_seconds']=43200
    return t

def test_long_window_is_explicit_and_leaves_historical_policies_unchanged():
    assert validate_trial(long_window())
    for policy in ('p1-resume-v1','p1-resume-v2','p1-time-window-v1'):
        t=long_window();t['execution_policy']=policy
        with pytest.raises(ValueError):validate_trial(t)

@pytest.mark.parametrize('damage',['model_time','total_time','endpoint','saved_qa','elapsed',
    'diagnostics','optimizer','updates','forwards','full_calls'])
def test_long_window_enforces_reserves_and_explicit_limits(damage):
    t=long_window()
    if damage=='model_time':t['budget']['segment_seconds']+=1
    elif damage=='total_time':t['budget']['total_seconds']+=1
    elif damage=='endpoint':t['budget']['endpoint_reserve_seconds']=299
    elif damage=='saved_qa':t['budget']['total_seconds']-=1
    elif damage=='elapsed':t['trajectory_budget']['model_seconds']+=1
    elif damage=='diagnostics':t.pop('diagnostics')
    elif damage=='optimizer':t['optimizer']['line_search']='previous-alpha-double'
    else:t['budget']['accepted_updates' if damage=='updates' else damage]+=1
    with pytest.raises(ValueError):validate_trial(t)

def test_uva_long_trial_preserves_exact_parent_cost_and_full_segment_allowance():
    from types import SimpleNamespace
    from tmdlab.restart import load_restart,elapsed_before,segment_allowance
    root=Path(__file__).parents[1]
    t=validate_trial(read(root/'trials/continuation-w16-feasibility-7h-uva-a01.json'))
    m,_=load_restart(root,t['start_checkpoint'][8:],t,
        SimpleNamespace(index={'identity':t['bundle_identity']}))
    assert m['counters']['accepted_updates']==46
    for key in ('accepted_updates','forwards','full_calls'):
        assert t['trajectory_budget'][key]==m['counters'][key]+t['budget'][key]
    prior=elapsed_before(root,m)
    assert prior==pytest.approx(2283.882704458083)
    assert segment_allowance(t,prior)==25200
    assert 0<=t['trajectory_budget']['model_seconds']-prior-25200<1

@pytest.mark.parametrize('damage',['reset','remaining','counter','reserve','phase','algorithm','elapsed'])
def test_resume_invalid_bindings_and_grants_fail_before_model(damage):
    t=resumed()
    if damage=='reset':t['restart_binding']['optimizer_history_reset']=True
    elif damage=='remaining':t['phases'][0]['updates']=59
    elif damage=='counter':t['trajectory_budget']['forwards']=4097
    elif damage=='reserve':t['budget']['endpoint_reserve_seconds']=0
    elif damage=='phase':t['phases'][0]['mu']=1e-5
    elif damage=='algorithm':t['optimizer']['line_search']='unregistered'
    elif damage=='elapsed':t['trajectory_budget']['model_seconds']=21601
    with pytest.raises(ValueError):validate_trial(t)
