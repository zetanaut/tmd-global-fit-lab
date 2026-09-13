"""Portable D1/D2 regressions and prior CPU safeguards; no real workers/Git."""
import copy
import json
import math
from pathlib import Path
import subprocess
import threading
import time
from types import SimpleNamespace
import pytest
from tmdlab import claim, run
from tmdlab.contracts import validate_trial
from tmdlab.io import read, digest, within

ROOT = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[1]
BUDGET = dict(rss_gib=4, gpu_gib=0, host_available_gib=8)

def trial():
    return read(REPO / 'trials/replay-w8-cpu-a01.json')

@pytest.mark.parametrize('key,value', [('forwards', 601), ('full_calls', 241), ('segment_seconds', 1801),
                                     ('gpu_gib', 21), ('rss_gib', 49), ('cpu_threads', 13),
                                     ('accepted_updates', 97), ('full_calls', 2.5), ('forwards', True)])
def test_spec_caps(key, value):
    t = trial(); t['budget'][key] = value
    with pytest.raises(ValueError): validate_trial(t)

@pytest.mark.parametrize('key,value', [('status', 'draft'), ('rows', 2289), ('dtype', 'float32'),
                                     ('source_identity', 'x'), ('metric_identity', 'x'),
                                     ('bundle_identity', 'x'), ('model_family', 'unverified')])
def test_spec_identity(key, value):
    t = trial(); t[key] = value
    with pytest.raises(ValueError): validate_trial(t)

def test_replay_cannot_train_and_continuation_cannot_overallocate():
    t = trial(); t['phases'] = [dict(mu=1e-6, updates=1)]
    with pytest.raises(ValueError): validate_trial(t)
    t['kind'] = 'continuation'; t['phases'][0]['updates'] = 97
    with pytest.raises(ValueError): validate_trial(t)

@pytest.mark.parametrize('payload', ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_strict_json_rejects_ambiguity(tmp_path, payload):
    p = tmp_path / 'bad.json'; p.write_text(payload)
    with pytest.raises(ValueError): read(p)

def test_overlay_path_escape_and_digest(tmp_path):
    for path in ('../escape', '/absolute'):
        with pytest.raises(ValueError): within(tmp_path, path)
    (tmp_path / 'link').symlink_to(tmp_path.parent)
    with pytest.raises(ValueError): within(tmp_path, 'link/outside')
    assert digest({'a': 1, 'b': 2}) == digest({'b': 2, 'a': 1})

def test_host_floor_numeric_overflow_must_be_rejected(tmp_path):
    text = json.dumps(trial()).replace('"host_available_gib": 8', '"host_available_gib": 1e309')
    p = tmp_path / 'overflow.json'; p.write_text(text)
    with pytest.raises(ValueError): validate_trial(read(p))

class FakeProcess:
    pid = 424242
    def __init__(self, seconds=None):
        self.code = None
        self.end = time.monotonic() + seconds if seconds is not None else None
    def poll(self):
        if self.end is not None and time.monotonic() >= self.end: self.code = 0
        return self.code
    def wait(self, timeout=None):
        if self.poll() is None: raise AssertionError('unexpected wait on live synthetic process')
        return self.code

def healthy(pid, gpu):
    assert not gpu
    return dict(monotonic=time.monotonic(), rss_gib=1., host_available_gib=16., accepted_updates=0, gpu_owned_gib=None)

@pytest.fixture
def fake_stop(monkeypatch):
    stopped = []
    def stop(process):
        stopped.append(process); process.code = -15
    monkeypatch.setattr(run, 'stop_owned', stop)
    return stopped

@pytest.mark.parametrize('mode,reason', [('stale', 'telemetry_stale_over_1s'),
                                       ('malformed', 'telemetry_failure'), ('high', 'resource_limit'),
                                       ('low_host', 'resource_limit')])
def test_supervisor_telemetry_fails_closed(tmp_path, fake_stop, mode, reason):
    owned, unrelated = FakeProcess(), FakeProcess()
    def sampler(pid, gpu):
        s = healthy(pid, gpu)
        if mode == 'stale': s['monotonic'] -= 2
        if mode == 'malformed': s['rss_gib'] = float('nan')
        if mode == 'high': s['rss_gib'] = 5
        if mode == 'low_host': s['host_available_gib'] = 7
        return s
    r = run.supervise(owned, deadline=time.monotonic()+3, budget=BUDGET, gpu=False, out=tmp_path, sampler=sampler)
    assert r['stop_reason'].startswith(reason)
    assert fake_stop == [owned] and unrelated.poll() is None

def test_deadline_does_not_wait_for_blocked_sampler(tmp_path, fake_stop):
    release, done = threading.Event(), threading.Event()
    def sampler(pid, gpu):
        try:
            release.wait(3)
            return healthy(pid, gpu)
        finally: done.set()
    owned = FakeProcess(); started = time.monotonic()
    try:
        r = run.supervise(owned, deadline=started+.15, budget=BUDGET, gpu=False, out=tmp_path, sampler=sampler)
        assert r['stop_reason'] == 'model_deadline'
        assert time.monotonic()-started < 2
        assert fake_stop == [owned]
    finally:
        release.set(); assert done.wait(1)

def test_healthy_samples_persist_peaks(tmp_path, fake_stop):
    owned = FakeProcess(.55)
    r = run.supervise(owned, deadline=time.monotonic()+3, budget=BUDGET, gpu=False, out=tmp_path, sampler=healthy)
    assert r['stop_reason'] is None and r['peaks']['samples'] >= 2
    assert r['peaks']['rss_gib'] == 1 and r['peaks']['host_available_min_gib'] == 16
    assert len((tmp_path / 'resources.ndjson').read_text().splitlines()) >= 2
    assert fake_stop == []

def test_cgroup_sample_unavailable_after_verified_owned_exit_is_not_live_failure(tmp_path,fake_stop):
    owned=FakeProcess(); calls=[]
    def sampler(pid,gpu):
        calls.append(pid)
        if len(calls)>1:
            owned.code=0
            raise ValueError('finite cgroup limit unavailable')
        return healthy(pid,gpu)
    result=run.supervise(owned,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=sampler)
    assert result['exit_code']==0 and result['stop_reason'] is None
    assert result['peaks']['samples']>=1
    assert 'finite cgroup limit' in result['terminal_sample_unavailable_after_owned_exit']
    assert fake_stop==[]

def test_terminal_sample_error_never_certifies_a_run_with_zero_valid_samples(tmp_path,fake_stop):
    owned=FakeProcess()
    def sampler(pid,gpu):
        owned.code=0
        raise ValueError('finite cgroup limit unavailable')
    result=run.supervise(owned,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=sampler)
    assert result['stop_reason']=='telemetry_missing_no_samples'
    assert result['resource_telemetry_status']=='unknown_no_samples'

def test_missing_cgroup_for_a_live_worker_still_fails_closed(tmp_path,fake_stop):
    owned=FakeProcess()
    def sampler(pid,gpu):raise ValueError('finite cgroup limit unavailable')
    result=run.supervise(owned,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=sampler)
    assert result['stop_reason'].startswith('telemetry_failure: ValueError: finite cgroup limit')
    assert fake_stop==[owned]

def test_term_to_kill_escalation_is_owned_only(monkeypatch):
    class Resistant(FakeProcess):
        def wait(self, timeout=None):
            if timeout == 2: raise subprocess.TimeoutExpired('synthetic', timeout)
            assert timeout == 5
            self.code = -9; return self.code
    signals = []
    monkeypatch.setattr(run.os, 'killpg', lambda pid, sig: signals.append((pid, sig)))
    owned = Resistant(); run.stop_owned(owned)
    assert signals == [(owned.pid, run.signal.SIGTERM), (owned.pid, run.signal.SIGKILL)]

def test_fast_exit_without_telemetry_must_not_certify_resources(tmp_path, fake_stop):
    release, done = threading.Event(), threading.Event()
    def sampler(pid, gpu):
        try:
            release.wait(3)
            return healthy(pid, gpu)
        finally: done.set()
    try:
        r = run.supervise(FakeProcess(.05), deadline=time.monotonic()+3, budget=BUDGET, gpu=False, out=tmp_path, sampler=sampler)
        assert r['peaks']['samples'] == 0
        assert r['stop_reason'] == 'telemetry_missing_no_samples'
        assert r['resource_telemetry_status'] == 'unknown_no_samples'
        assert r['peaks']['rss_gib'] is None
        assert r['peaks']['gpu_owned_gib'] is None
        assert r['peaks']['host_available_min_gib'] is None
        assert r['exit_code'] == 0
    finally:
        release.set(); assert done.wait(1)

def exercise_claim(monkeypatch, tmp_path, mode):
    calls, pushes, writes = [], [], []
    claimed = 'c' * 40
    count = 0
    def cmd(*args, **kwargs):
        nonlocal count
        calls.append(args)
        if args[0] == 'status': return ''
        if args[0] == 'rev-parse': return 'a' * 40
        if args[0] == 'remote': return 'https://github.com/zetanaut/tmd-global-fit-lab.git'
        if args[0] == 'ls-remote':
            count += 1
            if mode == 'already_claimed' or count > 1:
                return (('d' * 40 if mode == 'bad_readback' else claimed) + '\t' + args[-1])
            return ''
        if args[0] == 'commit-tree': return claimed
        return 'b' * 40
    monkeypatch.setattr(claim, 'cmd', cmd)
    monkeypatch.setattr(claim.subprocess, 'run', lambda argv, **kw: pushes.append((argv, kw)))
    monkeypatch.setattr(claim, 'write', lambda path, value: writes.append((path, value)))
    args = SimpleNamespace(trial=REPO / 'trials/replay-w8-cpu-a01.json', owner='synthetic-no-external-claim', out=tmp_path / 'not-a-real-claim.json')
    if mode != 'success':
        with pytest.raises(ValueError): claim.main(args)
        assert not writes
    else:
        claim.main(args)
        assert len(writes) == 1 and writes[0][1]['claim_commit'] == claimed
    if mode == 'already_claimed':
        assert pushes == []
    else:
        argv, kwargs = pushes[0]
        assert '--force-with-lease=refs/heads/claims/replay-w8-cpu-a01:' in argv
        assert kwargs == {'check': True}
    return calls

@pytest.mark.parametrize('mode', ['success', 'already_claimed', 'bad_readback'])
def test_claim_create_only_and_readback(monkeypatch, tmp_path, mode):
    exercise_claim(monkeypatch, tmp_path, mode)

@pytest.mark.parametrize('field', ['trial_id', 'trial_sha256', 'code_commit'])
def test_runner_rejects_mismatched_claim_before_output_or_dispatch(monkeypatch, tmp_path, field):
    from tmdlab.io import sha
    spec = REPO / 'trials/replay-w8-cpu-a01.json'
    receipt = dict(trial_id=trial()['trial_id'], trial_sha256=sha(spec), code_commit='a' * 40)
    receipt[field] = 'wrong'
    claim_path = tmp_path / 'synthetic-mismatch.json'
    claim_path.write_text(json.dumps(receipt))
    def git(*args):
        if args == ('rev-parse', '--show-toplevel'): return str(REPO)
        if args == ('rev-parse', 'HEAD'): return 'a' * 40
        if args == ('status', '--porcelain'): return ''
        raise AssertionError(args)
    monkeypatch.setattr(run, 'git', git)
    out = tmp_path / 'must-not-exist'
    args = SimpleNamespace(trial=spec, device='cpu', claim=claim_path, out=out)
    with pytest.raises(ValueError, match='claim/spec/code mismatch'): run.main(args)
    assert not out.exists()

def test_runner_rejects_cpu_spec_gpu_device_before_claim_or_dispatch(monkeypatch, tmp_path):
    def git(*args):
        if args == ('rev-parse', '--show-toplevel'): return str(REPO)
        if args == ('rev-parse', 'HEAD'): return 'a' * 40
        if args == ('status', '--porcelain'): return ''
        raise AssertionError(args)
    monkeypatch.setattr(run, 'git', git)
    args = SimpleNamespace(trial=REPO / 'trials/replay-w8-cpu-a01.json', device='cuda:0', claim=None, out=tmp_path / 'must-not-exist')
    with pytest.raises(ValueError, match='device differs'): run.main(args)
    assert not args.out.exists()

@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')], ids=['nan', 'positive_inf', 'negative_inf'])
@pytest.mark.parametrize('key', list(trial()['budget']))
def test_every_budget_field_rejects_nonfinite(key, value):
    t = trial(); t['budget'][key] = value
    with pytest.raises(ValueError, match='nonfinite'): validate_trial(t)

@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')], ids=['nan', 'positive_inf', 'negative_inf'])
@pytest.mark.parametrize('location', ['rows', 'seed', 'width', 'depth', 'phase_mu', 'phase_updates', 'extension'])
def test_all_nested_spec_numbers_reject_nonfinite(location, value):
    t = trial()
    if location in ('rows', 'seed'): t[location] = value
    elif location in ('width', 'depth'): t['model'][location] = value
    elif location.startswith('phase_'):
        t['kind'] = 'continuation'
        t['phases'] = [dict(mu=1e-6, updates=1)]
        t['phases'][0][location.removeprefix('phase_')] = value
    else: t['extension'] = {'nested': [1, {'value': value}]}
    with pytest.raises(ValueError, match='nonfinite'): validate_trial(t)

@pytest.mark.parametrize('token', ['1e309', '-1e309', 'NaN', 'Infinity', '-Infinity'])
@pytest.mark.parametrize('shape', ['scalar', 'array', 'nested'])
def test_json_rejects_all_nonfinite_spellings_at_any_depth(tmp_path, token, shape):
    payload = token if shape == 'scalar' else '[' + token + ']' if shape == 'array' else '{"extra":[{"number":' + token + '}]}'
    path = tmp_path / 'nonfinite.json'; path.write_text(payload)
    with pytest.raises(ValueError): read(path)

def test_finite_json_and_in_memory_specs_are_preserved(tmp_path):
    from tmdlab.io import require_finite_numbers, write
    value = {'finite': [1e308, -1e308, 1e-308, -0.0, 0, 10**400, True, False, None], 'text': 'Infinity'}
    path = tmp_path / 'finite.json'; write(path, value)
    loaded = read(path)
    assert loaded == value
    assert math.copysign(1, loaded['finite'][3]) == -1
    assert require_finite_numbers(value) is value
    assert all(validate_trial(read(p))['status'] == 'ready' for p in (REPO / 'trials').glob('*.json'))
    t = trial(); t['kind'] = 'continuation'; t['phase'] = 'P1'; t['phases'] = [dict(mu=1e-6, updates=96)]
    t['continuation_binding'] = dict(start_checkpoint_sha256='0'*64, start_q_per_measurement=1.,
        accepted_updates_before=160, optimizer_history_reset=True, allocation_id='p1-test-allocation',
        budget_origin='new_allocation', prior_phase='P0')
    original = copy.deepcopy(t)
    assert validate_trial(t) is t and t == original

@pytest.mark.parametrize('exit_code', [0, 7])
def test_already_exited_worker_has_unknown_not_zero_peaks(tmp_path, fake_stop, exit_code):
    p = FakeProcess(); p.code = exit_code
    r = run.supervise(p, deadline=time.monotonic()+3, budget=BUDGET, gpu=False, out=tmp_path, sampler=healthy)
    assert r['stop_reason'] == 'telemetry_missing_no_samples'
    assert r['resource_telemetry_status'] == 'unknown_no_samples'
    assert r['peaks'] == dict(rss_gib=None, gpu_owned_gib=None, host_available_min_gib=None, samples=0)
    assert r['exit_code'] == exit_code and not fake_stop
    assert (tmp_path / 'resources.ndjson').read_text() == ''
    assert json.loads(json.dumps(r, allow_nan=False)) == r

def test_deadline_reason_preserved_when_no_samples(tmp_path, fake_stop):
    release, done = threading.Event(), threading.Event()
    def blocked(pid, gpu):
        try:
            release.wait(3)
            return healthy(pid, gpu)
        finally: done.set()
    try:
        r = run.supervise(FakeProcess(), deadline=time.monotonic()-.1, budget=BUDGET, gpu=False, out=tmp_path, sampler=blocked)
        assert r['stop_reason'] == 'model_deadline'
        assert r['resource_telemetry_status'] == 'unknown_no_samples'
        assert r['peaks']['samples'] == 0 and r['peaks']['rss_gib'] is None
    finally:
        release.set(); assert done.wait(1)

def test_real_zero_synthetic_sample_is_distinct_from_no_sample(tmp_path, fake_stop):
    def zero(pid, gpu):
        return dict(healthy(pid, gpu), rss_gib=0.)
    r = run.supervise(FakeProcess(.25), deadline=time.monotonic()+3, budget=BUDGET, gpu=False, out=tmp_path, sampler=zero)
    assert r['stop_reason'] is None
    assert r['resource_telemetry_status'] == 'sampled'
    assert r['peaks']['samples'] >= 1 and r['peaks']['rss_gib'] == 0.

def test_failed_telemetry_keeps_specific_error_and_unknown_peaks(tmp_path, fake_stop):
    def bad(pid, gpu): raise ValueError('synthetic sample error')
    r = run.supervise(FakeProcess(), deadline=time.monotonic()+3, budget=BUDGET, gpu=False, out=tmp_path, sampler=bad)
    assert r['stop_reason'] == 'telemetry_failure: ValueError: synthetic sample error'
    assert r['resource_telemetry_status'] == 'unknown_no_samples'
    assert r['peaks']['samples'] == 0 and r['peaks']['rss_gib'] is None
