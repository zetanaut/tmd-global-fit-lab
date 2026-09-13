import json
import numpy as np
import pytest

import tmdlab.paired_feasibility as feasibility
from tmdlab.run import paired_launch_binding
from tmdlab.results import collect
from tmdlab.io import SOURCE_ID, METRIC_ID, write, read
from tmdlab.audit import paired_audit


class RejectingEngine:
    def __init__(self, *args, **kwargs):
        pass

    def evaluate(self, theta, cotangent=None, **kwargs):
        return np.array([2.0]), None

    def close(self):
        pass


class RejectingMetric:
    def describe(self, values):
        return {"q_per_measurement": 9.0, "min_T_over_sigma": 2.0}

    def score(self, values, mu):
        return None


class ExactEngine:
    def __init__(self, *args, **kwargs):
        pass

    def evaluate(self, theta, cotangent=None, **kwargs):
        values = np.array([theta[0] + 2.0])
        return values, None if cotangent is None else np.array([1.0])

    def close(self):
        pass


class ExactMetric:
    sigma = np.array([1.0])

    def describe(self, values):
        return {"q_per_measurement": float(values[0]), "min_T_over_sigma": float(values[0])}

    def score(self, values, mu):
        return dict(q_per_measurement=float(values[0]), objective=float(values[0]),
                    cotangent=np.array([1.0]), raw_cotangent=np.array([1.0]),
                    min_T_over_sigma=float(values[0]))


def test_infeasible_candidate_keeps_forward_evidence_and_crash_safe_counter(tmp_path, monkeypatch):
    monkeypatch.setattr(feasibility, "Engine", RejectingEngine)
    calls = feasibility.Calls(63, 18, tmp_path)
    with pytest.raises(ValueError, match="strictly feasible"):
        feasibility.evaluate(None, np.array([0.0]), None, RejectingMetric(), "cpu", 1, calls, 1,
                             float("inf"), tmp_path / "cell")
    assert (tmp_path / "cell" / "forward.npz").is_file()
    record = json.loads((tmp_path / "cell" / "cell.json").read_text())
    assert record["status"] == "failed" and record["spent"]["forwards"] == 1
    assert json.loads((tmp_path / "counters.json").read_text())["call_in_flight"] is False


def test_passing_cell_has_seven_forwards_two_vjps_and_endpoint_receipts(tmp_path, monkeypatch):
    monkeypatch.setattr(feasibility, "Engine", ExactEngine)
    calls = feasibility.Calls(63, 18, tmp_path)
    point = feasibility.evaluate(None, np.array([0.0]), None, ExactMetric(), "cpu", 1, calls, 1,
                                 float("inf"), tmp_path / "cell")
    assert point["spent"]["forwards"] == 7 and point["spent"]["full_calls"] == 2
    assert (tmp_path / "cell" / "raw-vjp.npz").is_file()
    assert json.loads((tmp_path / "cell" / "cell.json").read_text())["status"] == "passed"


def protocol(**changes):
    base = dict(source_checkpoint="anchor-w8", device="cuda:0", seeds=[1, 2, 3], radius=.01,
                min_diversity_rms=.001, cache_gib=12, max_forwards=300, max_full_calls=96, seconds=1800.)
    base.update(changes)
    return type("Args", (), base)()


def binding(args, **changes):
    base = dict(schema="tmd-paired-width-feasibility-launch-v1", trial_id="paired-width-feasibility-w03-a01",
                trial_sha256="a"*64, code_commit="b"*64, claim_commit="c"*64, claim_sha256="d"*64,
                spec_sha256="e"*64, bundle_identity="f"*64, source_checkpoint_sha256="0"*64,
                model_deadline_monotonic=20., **{key: getattr(args, key) for key in (
                    "source_checkpoint", "device", "seeds", "radius", "min_diversity_rms", "cache_gib",
                    "max_forwards", "max_full_calls", "seconds")})
    base.update(changes)
    return base


def test_binding_rejects_stale_or_changed_budget_protocol():
    args = protocol()
    assert feasibility.validate_launch_binding(binding(args), args, now=lambda: 10.) == 20.
    with pytest.raises(ValueError, match="deadline"):
        feasibility.validate_launch_binding(binding(args, model_deadline_monotonic=10.), args, now=lambda: 10.)
    with pytest.raises(ValueError, match="disagrees"):
        feasibility.validate_launch_binding(binding(args, max_forwards=301), args, now=lambda: 10.)
    with pytest.raises(ValueError, match="malformed"):
        feasibility.validate_launch_binding(binding(args, claim_sha256="not-a-hash"), args, now=lambda: 10.)


def test_diversity_failure_is_known_before_wide_cells_and_pair_error_is_measured():
    values = {1: np.array([1., 2.]), 2: np.array([1., 2.]), 3: np.array([2., 3.])}
    records, passed = feasibility.diversity_records([1, 2, 3], values, np.ones(2), .01)
    assert not passed and len(records) == 3 and records[0]["prediction_rms_fixed_sigma"] == 0.
    pair = feasibility.paired_transport_metrics(np.array([1., 2.]), np.array([1., 2.1]), np.ones(2), 3., 3.2)
    assert pair["prediction_error_fixed_sigma"] == pytest.approx(.1) and pair["q_error"] == pytest.approx(.2)


def test_supervisor_binding_uses_real_git_ids_and_exact_source_and_budget(tmp_path):
    source = tmp_path / "source.npz"; source.write_bytes(b"pinned source")
    spec = tmp_path / "spec.json"; spec.write_text("{}")
    claim = tmp_path / "claim.json"; claim.write_text("{}")
    class Bundle:
        def checkpoint(self, name):
            assert name == "anchor-w8"
            return {"path": "source.npz"}, {}
        def file(self, name):
            return source
    args = protocol()
    trial = dict(trial_id="paired-width-feasibility-w03-a01", bundle_identity="f"*64,
        start_checkpoint="anchor-w8", paired_start=dict(source_checkpoint_sha256=feasibility.sha(source),
        seeds=args.seeds, radius=args.radius, min_diversity_rms=args.min_diversity_rms),
        budget=dict(cache_gib=args.cache_gib, forwards=args.max_forwards, full_calls=args.max_full_calls,
                    segment_seconds=args.seconds))
    launch = paired_launch_binding(trial, spec, {"claim_commit":"c"*40}, claim, "b"*40, Bundle(), "cuda:0", 20.)
    assert feasibility.validate_launch_binding(launch, args, now=lambda: 10.) == 20.
    trial["budget"]["forwards"] += 1
    changed = paired_launch_binding(trial, spec, {"claim_commit":"c"*40}, claim, "b"*40, Bundle(), "cuda:0", 20.)
    with pytest.raises(ValueError, match="disagrees"):
        feasibility.validate_launch_binding(changed, args, now=lambda: 10.)


def test_result_collection_reads_paired_nested_worker_and_root_saved_audit(tmp_path):
    run=tmp_path/'run'; worker=run/'worker'; worker.mkdir(parents=True)
    trial=dict(schema='tmd-trial-v1',trial_id='paired-width-feasibility-w03-a01',source_identity=SOURCE_ID,
        metric_identity=METRIC_ID,bundle_identity='f'*64,kind='replay',phase='W03',model={'width':8,'depth':1},
        start_checkpoint='anchor-w8',execution_policy='paired-feasibility-v1')
    write(run/'trial.json',trial)
    write(run/'launch.json',dict(run_id='paired-width-feasibility-w03-a01-abcdef123456',trial_id=trial['trial_id'],
        trial_sha256='a'*64,code_commit='b'*40,bundle_identity=trial['bundle_identity'],device='cuda:0',slurm={},claim={}))
    write(run/'supervisor.json',dict(stop_reason=None))
    write(worker/'worker-summary.json',dict(status='completed',stop_reason=None,counters={'forwards':63,'full_calls':18,'accepted_updates':0}))
    write(run/'audit.json',dict(passed=True,status='verified',model_calls=0))
    artifact=tmp_path/'archive.tar.gz'; artifact.write_bytes(b'archive')
    out=tmp_path/'results'
    collect(type('Args',(),dict(run=run,artifact=artifact,
        artifact_url='https://github.com/zetanaut/tmd-global-fit-lab/releases/download/run/archive.tar.gz',out=out))())
    record=read(next((out/trial['trial_id']).glob('*.json')))
    assert record['status']=='completed' and record['counters']['forwards']==63 and record['audit']['passed']


def test_paired_audit_rejects_identical_narrow_starts_before_any_architecture_claim(tmp_path):
    class Metric:
        sigma=np.ones(2290)
        def score(self, values, mu):
            return dict(q_per_measurement=float(values.mean()), min_T_over_sigma=float(values.min()))
    out=tmp_path/'run'; worker=out/'worker'; worker.mkdir(parents=True)
    seeds=[1,2,3]; source_hash='a'*64
    write(out/'trial.json',dict(paired_start=dict(seeds=seeds,min_diversity_rms=.001,source_checkpoint_sha256=source_hash),
        source_identity=SOURCE_ID,metric_identity=METRIC_ID,bundle_identity='b'*64,start_checkpoint='anchor-w8',
        budget=dict(forwards=300,full_calls=96)))
    candidates={}
    for seed in seeds:
        widths={}
        for width,count in ((8,1570),(16,2882),(24,4706)):
            path=worker/'starts'/f'seed-{seed}-w{width}.npz'
            theta=np.full(count,float(seed)); values=np.ones(2290); gradient=np.ones(count)
            feasibility.save_npz(path,theta=theta,values=values,raw_gradient=gradient,penalized_gradient=gradient)
            cell=dict(endpoint_path=str(path.relative_to(worker)),endpoint_sha256=feasibility.sha(path),
                directional=[dict(passed=True,attempts=[dict(feasible=True,error=0.)])]*2)
            if width==8:
                candidate_hash=__import__('hashlib').sha256(np.ascontiguousarray(theta).tobytes()).hexdigest()
            else:
                cell['paired_to_width8']=dict(prediction_error_fixed_sigma=0.,prediction_rms_fixed_sigma=0.,q_error=0.)
            widths[str(width)]=cell
        candidates[str(seed)]=dict(receipt=dict(seed=seed,candidate_parameter_sha256=candidate_hash),widths=widths)
    write(worker/'paired-feasibility.json',dict(status='passed',rows=2290,dtype='float64',source_identity=SOURCE_ID,
        metric_identity=METRIC_ID,bundle_identity='b'*64,source_checkpoint='anchor-w8',source_checkpoint_sha256=source_hash,
        seeds=seeds,candidates=candidates,counters=dict(accepted_updates=0,forwards=63,full_calls=18,call_in_flight=False)))
    result=paired_audit(Metric(),out)
    assert not result['passed'] and 'candidate diversity' in result['failures']
