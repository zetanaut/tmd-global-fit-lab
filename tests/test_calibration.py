import pytest
from tmdlab.calibration import decide,RESTART

def arms():
    control=dict(policy='unit-backtracking',start=RESTART,comparable=True,q=16.,objective=8.,
        new_forwards=200,seed=1,model=dict(width=8,depth=1),bundle='b',metric='m',source='s')
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
