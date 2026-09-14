"""Positivity evidence must identify all failed rows without changing decisions."""
import json
from types import SimpleNamespace

import numpy as np

from tmdlab.diagnostics import OptimizationDiagnostics, gradient_blocks
from tmdlab.io import read


def test_candidate_diagnostics_distinguish_positivity_and_armijo_rejections(tmp_path):
    metric=SimpleNamespace(info=dict(ids=['a','b','c','d']),sigma=np.array([2.,1.,1.,1.]))
    diagnostics=OptimizationDiagnostics(tmp_path,metric,[])
    context=dict(next_segment_update=1,next_cumulative_update=178)
    counts=dict(forwards=10,full_calls=2);prior=dict(forwards=1438,full_calls=205)
    values=np.array([0.,-2e-8,1e-8,1.])
    original=values.copy()
    diagnostics.candidate(context,values,None,1.,1,1.,counts,prior,1.)
    diagnostics.candidate(context,np.ones(4),dict(objective=2.,q_per_measurement=4.),
        .5,2,1.,counts,prior,2.)
    diagnostics.candidate(context,np.ones(4),dict(objective=.5,q_per_measurement=1.),
        .25,3,1.,counts,prior,3.)
    assert np.array_equal(original,values)
    records=[json.loads(line) for line in (tmp_path/'line-search.ndjson').read_text().splitlines()]
    assert [r['verdict'] for r in records]==['infeasible','armijo_rejected','armijo_passed']
    assert records[0]['violating_row_indices']==[0,1,2]
    assert records[0]['violating_T_over_sigma']==[0.,-2e-8,1e-8]
    np.testing.assert_allclose(records[0]['violating_margins'],[-1e-8,-3e-8,0.],rtol=1e-14,atol=0)
    assert records[0]['minimum_observation_id']=='b'
    assert records[0]['cumulative_forwards']==1448
    assert dict(diagnostics.violations)=={0:1,1:1,2:1}
    assert read(tmp_path/'diagnostic-rows.json')['observation_ids']==['a','b','c','d']


def test_gradient_diagnostics_respect_parameter_blocks():
    schema=[dict(name='incoming.width',shape=[2]),dict(name='cs.bias',shape=[1])]
    assert gradient_blocks(np.array([3.,4.,12.]),schema)=={
        'incoming.width':dict(parameters=2,l2=5.,maximum=4.),
        'cs.bias':dict(parameters=1,l2=12.,maximum=12.)}
