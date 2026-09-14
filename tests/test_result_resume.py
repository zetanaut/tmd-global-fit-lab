"""Result collection retains cumulative work, including post-checkpoint calls."""
from types import SimpleNamespace

import numpy as np
import pytest

from tmdlab.io import METRIC_ID, SOURCE_ID, read, sha, write
from tmdlab.restart import COUNTERS, pack_state
from tmdlab.results import collect, validate_record


@pytest.mark.parametrize('policy,summary_missing', [
    ('p1-resume-v1', False), ('p1-resume-v2', False), ('p1-resume-v2', True),
])
def test_resumed_result_reconciles_final_calls_and_preserves_prior_costs(
        tmp_path, policy, summary_missing):
    run = tmp_path / 'run'
    run.mkdir()
    trial = dict(trial_id='continuation-test', source_identity=SOURCE_ID,
        metric_identity=METRIC_ID, kind='continuation', phase='P1', model={'width': 8},
        start_checkpoint='restart:' + 'a' * 64, execution_policy=policy,
        trajectory_budget=dict(accepted_updates=96, forwards=4096,
                               full_calls=512, model_seconds=21600))
    write(run / 'trial.json', trial)
    write(run / 'launch.json', dict(run_id='continuation-test-abcdef123456',
        trial_id=trial['trial_id'], trial_sha256=sha(run / 'trial.json'),
        code_commit='b' * 40, bundle_identity='c' * 64, device='cuda:0',
        slurm={}, claim={}, model_seconds_before=1234.5))
    write(run / 'supervisor.json', dict(elapsed_seconds=100.,
        stop_reason='model_deadline' if summary_missing else None))
    counts = dict.fromkeys(COUNTERS, 0)
    counts.update(accepted_updates=82, forwards=700, full_calls=110)
    point = dict(theta=np.ones(3), values=np.ones(2290), gradient=np.ones(3))
    states = [dict(values=point['values'], q_per_measurement=1.,
                   gradient_max=1., mu=1e-6)]
    np.savez_compressed(run / 'restart.npz',
        **pack_state(point, [], states, counts, mu=1e-6))
    np.savez_compressed(run / 'last.npz', theta=point['theta'],
        values=point['values'], penalized_gradient=point['gradient'])
    write(run / 'audit.json', dict(passed=True, endpoint_path='last.npz',
        endpoint_sha256=sha(run / 'last.npz')))
    # A final endpoint VJP was charged after the accepted optimizer state.
    charged = dict(counts, forwards=701, full_calls=111)
    segment = dict.fromkeys(COUNTERS, 0)
    segment.update(accepted_updates=1, forwards=11, full_calls=3)
    write(run / 'counters.json', dict(segment, trajectory_counters=charged))
    if not summary_missing:
        write(run / 'worker-summary.json', dict(status='completed',
            stop_reason='phase_schedule_complete', counters=segment,
            trajectory_counters=charged, optimizer_history_reset=False,
            plateau=dict(eligible=True, passed=False)))
    artifact = tmp_path / 'artifact.tar.gz'
    artifact.write_bytes(b'test archive')
    args = SimpleNamespace(run=run, artifact=artifact, out=tmp_path / 'results',
        artifact_url='https://github.com/zetanaut/tmd-global-fit-lab/releases/download/test/artifact.tar.gz')
    collect(args)
    path = args.out / trial['trial_id'] / 'continuation-test-abcdef123456.json'
    record = validate_record(read(path))
    assert record['status'] == ('partial' if summary_missing else 'completed')
    assert record['counters']['accepted_updates'] == 1
    assert record['trajectory_counters'] == charged
    assert record['trajectory_budget'] == trial['trajectory_budget']
    assert record['model_seconds_before'] == 1234.5
    assert record['trajectory_model_seconds'] == 1334.5
    assert record['worker_summary_missing'] is summary_missing
    original = path.read_bytes()
    with pytest.raises(ValueError, match='immutable result already exists'):
        collect(args)
    assert path.read_bytes() == original
