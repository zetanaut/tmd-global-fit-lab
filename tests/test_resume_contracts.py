from pathlib import Path
import pytest
from tmdlab.io import read
from tmdlab.contracts import validate_trial

def resumed():
    t=read(Path(__file__).parents[1]/'trials/continuation-w16-p1-a01.json')
    t.update(execution_policy='p1-resume-v1',start_checkpoint='restart:'+'0'*64,
        restart_binding=dict(parent_run_id='continuation-w16-p1-a01-test',state_sha256='0'*64,
            accepted_updates_before=38,optimizer_history_reset=False),
        trajectory_budget=dict(accepted_updates=96,forwards=4096,full_calls=512),
        optimizer=dict(line_search='unit-backtracking'))
    t['phases'][0]['updates']=58
    t['budget'].update(segment_seconds=13200,total_seconds=13800,forwards=4096,full_calls=512,endpoint_reserve_seconds=120)
    return t

def test_extended_policy_preserves_legacy_ceilings():
    assert validate_trial(resumed())
    t=resumed(); t.pop('execution_policy')
    with pytest.raises(ValueError):validate_trial(t)

@pytest.mark.parametrize('damage',['reset','remaining','counter','reserve','phase','algorithm'])
def test_resume_invalid_bindings_and_grants_fail_before_model(damage):
    t=resumed()
    if damage=='reset':t['restart_binding']['optimizer_history_reset']=True
    elif damage=='remaining':t['phases'][0]['updates']=59
    elif damage=='counter':t['trajectory_budget']['forwards']=4097
    elif damage=='reserve':t['budget']['endpoint_reserve_seconds']=0
    elif damage=='phase':t['phases'][0]['mu']=1e-5
    elif damage=='algorithm':t['optimizer']['line_search']='unregistered'
    with pytest.raises(ValueError):validate_trial(t)
