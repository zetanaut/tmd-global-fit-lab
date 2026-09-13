"""Bounded all-observable feasibility and pairing checks for candidate starts.

This is deliberately not an optimizer.  It turns candidate-only paired starts
into reviewable start artifacts only after every width has passed the fixed
all-row feasibility, replay and directional checks on one actual backend.
"""
import argparse
from dataclasses import asdict
import math
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import re

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmdlab.io import read, write, sha, utc, SOURCE_ID, METRIC_ID

# Populated only after CLI parsing so syntax and lightweight unit tests do not
# require the allocation's Torch installation.  Explicit names also make the
# evaluator injectable in CPU-only tests.
Bundle = Engine = Metric = Config = build = flat = put = schema = paired_width_candidates = None


def save_npz(path, **arrays):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".npz", delete=False) as f:
        pending = Path(f.name)
    try:
        np.savez_compressed(pending, **arrays)
        with pending.open("rb") as f:
            os.fsync(f.fileno())
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def _finite(value, name):
    if not np.isfinite(value).all():
        raise ValueError(f"nonfinite {name}")


class Calls:
    def __init__(self, max_forwards, max_full, out):
        self.max_forwards, self.max_full = max_forwards, max_full
        self.forwards = self.full_calls = 0
        self.by_kind = {}
        self.in_flight = False
        self.out = Path(out)

    def receipt(self, *, in_flight=None):
        if in_flight is not None:
            self.in_flight = in_flight
        value = dict(forwards=self.forwards, full_calls=self.full_calls, by_kind=self.by_kind,
                     accepted_updates=0, time_utc=utc(), call_in_flight=self.in_flight)
        write(self.out / "counters.json", value)
        return value

    def dispatch(self, engine, theta, cotangent=None, deadline=None, *, kind):
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("paired feasibility dispatch deadline")
        if self.forwards >= self.max_forwards or cotangent is not None and self.full_calls >= self.max_full:
            raise RuntimeError("paired feasibility call budget exhausted")
        self.forwards += 1
        if cotangent is not None:
            self.full_calls += 1
        self.by_kind[kind] = self.by_kind.get(kind, 0) + 1
        self.receipt(in_flight=True)
        result = engine.evaluate(theta, cotangent, deadline=deadline)
        self.receipt(in_flight=False)
        return result


def directional(engine, theta, point, metric, calls, rng, deadline, cell_out):
    records = []
    for direction_index in range(2):
        d = rng.normal(size=theta.size)
        d /= np.linalg.norm(d)
        analytic = float(point["gradient"] @ d)
        h, attempts, passed = 1e-5, [], False
        write(Path(cell_out) / "directional.json", dict(status="running", records=records + [
            dict(direction=direction_index, passed=False, attempts=attempts)]))
        while h >= 1e-10:
            plus, _ = calls.dispatch(engine, theta + h*d, deadline=deadline, kind="directional_forward")
            minus, _ = calls.dispatch(engine, theta - h*d, deadline=deadline, kind="directional_forward")
            p, m = metric.score(plus, point["mu"]), metric.score(minus, point["mu"])
            error = None if p is None or m is None else abs((p["objective"] - m["objective"]) / (2*h) - analytic)
            attempts.append(dict(h=h, error=error, feasible=p is not None and m is not None))
            write(Path(cell_out) / "directional.json", dict(status="running", records=records + [
                dict(direction=direction_index, passed=False, attempts=attempts)]))
            if error is not None and error < 2e-6:
                passed = True
                break
            h *= .5
        records.append(dict(direction=direction_index, passed=passed, attempts=attempts))
        write(Path(cell_out) / "directional.json", dict(status="passed" if passed else "failed", records=records))
        if not passed:
            raise ValueError("paired feasibility directional check failed")
    return records


def evaluate(model, theta, bundle, metric, device, cache_gib, calls, seed, deadline, cell_out):
    """Persist every endpoint before deciding whether it passed a gate.

    A failed feasibility candidate is experimental evidence, not disposable
    scratch data.  The caller supplies an exclusive cell directory so its
    inputs, forward values, gradients and directional probes survive timeout
    or a later gate failure.
    """
    cell_out = Path(cell_out)
    cell_out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    opening = calls.receipt(in_flight=False)
    write(cell_out / "cell.json", dict(status="running", started_utc=utc(),
        theta_sha256=_theta_digest(theta), counters_before=opening))
    save_npz(cell_out / "input.npz", theta=theta)
    engine = None
    try:
        engine = Engine(model, bundle, device, cache_gib=cache_gib, deadline=deadline)
        values, _ = calls.dispatch(engine, theta, deadline=deadline, kind="base_forward")
        save_npz(cell_out / "forward.npz", theta=theta, values=values)
        forward_description = metric.describe(values)
        write(cell_out / "forward.json", forward_description)
        point = metric.score(values, 1e-6)
        if point is None:
            raise ValueError("candidate is not strictly feasible")
        replay, gradient = calls.dispatch(engine, theta, point["cotangent"], deadline=deadline, kind="penalized_vjp")
        save_npz(cell_out / "penalized-vjp.npz", theta=theta, values=replay, gradient=gradient)
        if not np.array_equal(values, replay):
            raise ValueError("same-device forward/VJP mismatch")
        raw_values, raw_gradient = calls.dispatch(engine, theta, point["raw_cotangent"], deadline=deadline, kind="raw_vjp")
        save_npz(cell_out / "raw-vjp.npz", theta=theta, values=raw_values, gradient=raw_gradient)
        if not np.array_equal(values, raw_values):
            raise ValueError("same-device raw VJP mismatch")
        _finite(gradient, "penalized gradient")
        _finite(raw_gradient, "raw gradient")
        point.update(theta=theta.copy(), values=values, gradient=gradient, raw_gradient=raw_gradient,
                     raw_gradient_max=float(np.abs(raw_gradient).max()), gradient_max=float(np.abs(gradient).max()), mu=1e-6)
        point["directional"] = directional(engine, theta, point, metric, calls, np.random.default_rng(seed), deadline, cell_out)
        if time.monotonic() >= deadline:
            raise TimeoutError("paired feasibility endpoint completed after deadline")
        point["spent"] = dict(forwards=calls.forwards-opening["forwards"],
            full_calls=calls.full_calls-opening["full_calls"], model_seconds=time.monotonic()-started)
        write(cell_out / "cell.json", dict(status="passed", ended_utc=utc(), theta_sha256=_theta_digest(theta),
            diagnostics=forward_description, spent=point["spent"], counters_after=calls.receipt(in_flight=False)))
        return point
    except Exception as exc:
        write(cell_out / "cell.json", dict(status="failed", ended_utc=utc(), theta_sha256=_theta_digest(theta),
            error=str(exc), spent=dict(forwards=calls.forwards-opening["forwards"],
                full_calls=calls.full_calls-opening["full_calls"], model_seconds=time.monotonic()-started),
            counters_after=calls.receipt()))
        raise
    finally:
        if engine is not None:
            engine.close()


def _theta_digest(theta):
    return __import__("hashlib").sha256(np.ascontiguousarray(theta, dtype=np.float64).tobytes()).hexdigest()


def validate_launch_binding(binding, args, *, now=time.monotonic):
    """Validate the immutable supervisor receipt before importing Torch.

    The supervisor authenticates the commit/claim/spec files.  This worker
    independently rejects a copied receipt paired with altered CLI protocol
    limits, input identity, device, or a stale absolute model deadline.
    """
    required = ("schema", "trial_id", "trial_sha256", "code_commit", "claim_commit", "claim_sha256", "spec_sha256",
                "bundle_identity", "source_checkpoint", "source_checkpoint_sha256", "device", "seeds",
                "radius", "min_diversity_rms", "cache_gib", "max_forwards", "max_full_calls", "seconds",
                "model_deadline_monotonic")
    if binding.get("schema") != "tmd-paired-width-feasibility-launch-v1" or any(k not in binding for k in required[1:]):
        raise ValueError("external claim/source/deadline launch binding required")
    for key in ("trial_sha256", "claim_sha256", "spec_sha256", "bundle_identity", "source_checkpoint_sha256"):
        if not isinstance(binding[key], str) or not re.fullmatch(r"[0-9a-f]{64}", binding[key]):
            raise ValueError("malformed immutable launch identity: " + key)
    for key in ("code_commit", "claim_commit"):
        if not isinstance(binding[key], str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", binding[key]):
            raise ValueError("malformed immutable launch identity: " + key)
    expected = dict(source_checkpoint=args.source_checkpoint, device=args.device, seeds=args.seeds,
                    radius=args.radius, min_diversity_rms=args.min_diversity_rms, cache_gib=args.cache_gib,
                    max_forwards=args.max_forwards, max_full_calls=args.max_full_calls, seconds=args.seconds)
    if any(binding[k] != value for k, value in expected.items()):
        raise ValueError("launch binding disagrees with requested candidate protocol")
    external_deadline = float(binding["model_deadline_monotonic"])
    if not math.isfinite(external_deadline) or external_deadline <= now():
        raise ValueError("external model deadline is invalid or expired")
    return external_deadline


def diversity_records(seeds, narrow_values, sigma, threshold):
    records = []
    for i, left in enumerate(seeds):
        for right in seeds[i+1:]:
            delta = (narrow_values[left] - narrow_values[right]) / sigma
            rms = float(np.sqrt(np.mean(delta**2)))
            records.append(dict(left_seed=left, right_seed=right, prediction_rms_fixed_sigma=rms,
                prediction_max_fixed_sigma=float(np.abs(delta).max())))
    return records, all(item["prediction_rms_fixed_sigma"] >= threshold for item in records)


def paired_transport_metrics(narrow, partner, sigma, narrow_q, partner_q):
    delta = np.abs(partner - narrow) / sigma
    return dict(prediction_error_fixed_sigma=float(delta.max()),
        prediction_rms_fixed_sigma=float(np.sqrt(np.mean(delta**2))), q_error=abs(partner_q - narrow_q))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", required=True)
    p.add_argument("--source-checkpoint", default="anchor-w8")
    p.add_argument("--device", required=True)
    p.add_argument("--seeds", type=int, nargs=3, required=True)
    p.add_argument("--radius", type=float, required=True)
    p.add_argument("--min-diversity-rms", type=float, required=True)
    p.add_argument("--cache-gib", type=int, default=12)
    p.add_argument("--max-forwards", type=int, default=300)
    p.add_argument("--max-full-calls", type=int, default=96)
    p.add_argument("--seconds", type=float, required=True)
    p.add_argument("--launch-binding", required=True,
                   help="external supervisor-written immutable claim/source/deadline binding")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    # Keep ``--help`` and syntax review usable on the lightweight transfer
    # environment; actual feasibility evaluation requires the pinned torch
    # environment inside the allocation.
    global Bundle, Engine, Metric, Config, build, flat, put, schema, paired_width_candidates
    from tmdlab.bundle import Bundle
    from tmdlab.engine import Engine
    from tmdlab.metric import Metric
    from tmdlab.models import Config, build, flat, put, schema
    from tmdlab.paired_starts import paired_width_candidates
    if len(set(a.seeds)) != 3 or not (math.isfinite(a.radius) and 0 < a.radius <= .1):
        raise ValueError("three distinct seeds and a finite radius in (0,.1] are required")
    if not math.isfinite(a.min_diversity_rms) or not 0 < a.min_diversity_rms < 1:
        raise ValueError("finite diversity threshold in (0,1) required")
    if a.max_forwards < 63 or a.max_full_calls < 18 or not math.isfinite(a.seconds) or a.seconds <= 0:
        raise ValueError("insufficient bounded feasibility budget")
    binding = read(a.launch_binding)
    external_deadline = validate_launch_binding(binding, a)
    out = Path(a.out)
    if out.exists():
        raise ValueError("feasibility output already exists")
    out.mkdir(parents=True)
    write(out / "launch.json", dict(schema="tmd-paired-width-feasibility-launch-v1", started_utc=utc(), binding=binding,
        bundle=str(Path(a.bundle).resolve()), source_checkpoint=a.source_checkpoint, device=a.device,
        seeds=a.seeds, radius=a.radius, min_diversity_rms=a.min_diversity_rms,
        max_forwards=a.max_forwards, max_full_calls=a.max_full_calls, seconds=a.seconds))
    calls = Calls(a.max_forwards, a.max_full_calls, out)
    calls.receipt(in_flight=False)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(RuntimeError("SIGTERM")))
    try:
        import torch
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        write(out / "environment.json", dict(dtype="float64", deterministic_algorithms=True, TF32=False,
            torch_threads=torch.get_num_threads(), torch_cuda_build=torch.version.cuda,
            gpu_name=torch.cuda.get_device_name(0) if a.device.startswith("cuda") else None))
        deadline = min(time.monotonic() + a.seconds, external_deadline)
        bundle = Bundle(a.bundle)
        if bundle.index["identity"] != binding["bundle_identity"]:
            raise ValueError("launch binding bundle identity mismatch")
        metric = Metric(bundle)
        entry, saved = bundle.checkpoint(a.source_checkpoint)
        if sha(bundle.file(entry["path"])) != binding["source_checkpoint_sha256"]:
            raise ValueError("launch binding source checkpoint mismatch")
        cfg = Config(**entry["model"])
        if cfg.width != 8 or cfg.depth != 1:
            raise ValueError("paired-width feasibility source must be depth1 width8")
        source = build(cfg, a.seeds[0])
        if schema(source) != entry["parameter_schema"]:
            raise ValueError("source schema mismatch")
        put(source, saved["theta"])
        candidates = paired_width_candidates(source, seeds=tuple(a.seeds), target_widths=(16, 24), radius=a.radius)
        write(out / "candidates.json", dict(schema=candidates["schema"], source_model=candidates["source_model"],
            narrow_seeds=candidates["narrow_seeds"], target_widths=candidates["target_widths"], radius=candidates["radius"],
            candidates={str(seed): dict(receipt=item["receipt"], transports={str(width): item["partners"][width]["transport"]
                for width in (16, 24)}) for seed, item in candidates["candidates"].items()}))
        results, narrow_values = {}, {}
        # First establish that all three genuinely distinct narrow candidates
        # meet the all-row gates.  This avoids spending six widened evaluations
        # when the start set cannot support the planned multi-start comparison.
        for seed in a.seeds:
            item = candidates["candidates"][seed]
            seed_result = dict(receipt=item["receipt"], widths={})
            width, model = 8, item["narrow"]
            write(out / "active-cell.json", dict(seed=seed, width=width, started_utc=utc(), counters=calls.receipt(in_flight=False)))
            point = evaluate(model, flat(model), bundle, metric, a.device, a.cache_gib, calls,
                             seed * 1009 + width, deadline, out / "evidence" / f"seed-{seed}-w{width}")
            file = out / "starts" / f"seed-{seed}-w{width}.npz"
            save_npz(file, theta=point["theta"], values=point["values"], raw_gradient=point["raw_gradient"],
                     penalized_gradient=point["gradient"])
            seed_result["widths"][str(width)] = dict(q_per_measurement=point["q_per_measurement"],
                min_T_over_sigma=point["min_T_over_sigma"], raw_gradient_max=point["raw_gradient_max"],
                penalized_gradient_max=point["gradient_max"], directional=point["directional"], spent=point["spent"],
                endpoint_path=str(file.relative_to(out)), endpoint_sha256=sha(file))
            write(out / "cells" / f"seed-{seed}-w{width}.json", seed_result["widths"][str(width)])
            narrow_values[seed] = point["values"]
            results[str(seed)] = seed_result
        diversity, diverse = diversity_records(a.seeds, narrow_values, metric.sigma, a.min_diversity_rms)
        if not diverse:
            write(out / "diversity.json", dict(threshold=a.min_diversity_rms, pairs=diversity,
                passed=False, failure="candidate diversity threshold not met"))
            raise ValueError("candidate diversity threshold not met")
        write(out / "diversity.json", dict(threshold=a.min_diversity_rms, pairs=diversity, passed=True))
        for seed in a.seeds:
            item, seed_result = candidates["candidates"][seed], results[str(seed)]
            for width in (16, 24):
                model = item["partners"][width]["model"]
                write(out / "active-cell.json", dict(seed=seed, width=width, started_utc=utc(), counters=calls.receipt(in_flight=False)))
                point = evaluate(model, flat(model), bundle, metric, a.device, a.cache_gib, calls,
                                 seed * 1009 + width, deadline, out / "evidence" / f"seed-{seed}-w{width}")
                file = out / "starts" / f"seed-{seed}-w{width}.npz"
                save_npz(file, theta=point["theta"], values=point["values"], raw_gradient=point["raw_gradient"],
                         penalized_gradient=point["gradient"])
                cell = dict(q_per_measurement=point["q_per_measurement"], min_T_over_sigma=point["min_T_over_sigma"],
                    raw_gradient_max=point["raw_gradient_max"], penalized_gradient_max=point["gradient_max"],
                    directional=point["directional"], spent=point["spent"], transport=item["partners"][width]["transport"],
                    endpoint_path=str(file.relative_to(out)), endpoint_sha256=sha(file))
                pair = paired_transport_metrics(narrow_values[seed], point["values"], metric.sigma,
                    seed_result["widths"]["8"]["q_per_measurement"], point["q_per_measurement"])
                write(out / "evidence" / f"seed-{seed}-w{width}" / "paired-transport.json", pair)
                if pair["prediction_error_fixed_sigma"] > 1e-7 or pair["q_error"] > 1e-8:
                    raise ValueError("function-preserving paired transport replay failed")
                cell["paired_to_width8"] = pair
                seed_result["widths"][str(width)] = cell
                write(out / "cells" / f"seed-{seed}-w{width}.json", cell)
        report = dict(schema="tmd-paired-width-feasibility-v1", status="passed", generated_utc=utc(),
            source_identity=SOURCE_ID, metric_identity=METRIC_ID, bundle_identity=bundle.index["identity"],
            source_checkpoint=a.source_checkpoint, source_checkpoint_sha256=sha(bundle.file(entry["path"])),
            source_theta_sha256=candidates["candidates"][a.seeds[0]]["receipt"]["source_parameter_sha256"],
            model=asdict(cfg), rows=2290, dtype="float64", seeds=a.seeds, radius=a.radius,
            widths=[8, 16, 24], min_diversity_rms=a.min_diversity_rms, diversity=diversity,
            candidates=results, counters=calls.receipt(in_flight=False),
            note="Bounded feasibility/replay evidence only; these starts need separate immutable registration and trial specifications before optimization.")
        write(out / "paired-feasibility.json", report)
        write(out / "worker-summary.json", dict(status="completed", stop_reason=None, counters=calls.receipt(in_flight=False)))
        print(out / "paired-feasibility.json")
    except Exception as exc:
        write(out / "worker-summary.json", dict(status="partial" if calls.forwards else "failed", stop_reason=str(exc), counters=calls.receipt()))
        raise


if __name__ == "__main__":
    main()
