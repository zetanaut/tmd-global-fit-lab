#!/usr/bin/env python3
"""Review an archived width-8 segment using saved arrays only; no model calls."""
import argparse
import hashlib
from pathlib import Path
import sys
import tarfile

import numpy as np
from scipy.linalg import cho_solve

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmdlab.bundle import Bundle
from tmdlab.io import read, sha, write
from tmdlab.metric import Metric
from tmdlab.results import validate_record


def describe(x):
    x = np.asarray(x, dtype=np.float64)
    if not x.size or not np.isfinite(x).all():
        raise ValueError("empty or nonfinite saved diagnostic")
    return dict(mean=float(x.mean()), rms=float(np.sqrt(np.mean(x*x))),
                minimum=float(x.min()), maximum=float(x.max()),
                absolute_median=float(np.median(np.abs(x))))


def fixed_split(values, fixed, sigma):
    """Subtract the fixed matched contribution, NOT an isolated FO term.

    These are saved endpoint amplitudes, not derivatives, feasible response
    bounds or an inference about what a different network could achieve.
    """
    if (values.shape != fixed.shape or values.shape != sigma.shape
            or not np.isfinite([values, fixed, sigma]).all() or np.any(sigma <= 0)):
        raise ValueError("invalid fixed-contribution inputs")
    return (values-fixed)/sigma


def review(args):
    run = args.run.resolve()
    record = validate_record(read(args.record))
    if sha(args.archive) != record['artifact']['sha256']:
        raise ValueError('downloaded archive digest mismatch')
    # Verify the downloaded archive against every immutable result file AND
    # the local arrays being analyzed, without extracting or editing the run.
    with tarfile.open(args.archive, 'r:gz') as archive:
        members = archive.getmembers()
        expected = {run.name+'/'+name for name in record['files']}
        actual = {m.name for m in members if m.isfile()}
        if actual != expected or any(m.issym() or m.islnk() for m in members):
            raise ValueError('unexpected archive inventory or links')
        if len(actual) != sum(m.isfile() for m in members):
            raise ValueError('duplicate archive members')
        for name, ref in record['files'].items():
            member = archive.getmember(run.name+'/'+name)
            with archive.extractfile(member) as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != ref['sha256'] or member.size != ref['bytes'] or sha(run/name) != digest:
                raise ValueError('archive/local/record mismatch: '+name)
    bundle = Bundle(args.bundle, verify_all=True)
    metric = Metric(bundle)
    with np.load(run/'initial.npz', allow_pickle=False) as z:
        initial = z['values'].copy()
    with np.load(run/'last.npz', allow_pickle=False) as z:
        final = z['values'].copy()
        raw, penalized = z['raw_gradient'].copy(), z['penalized_gradient'].copy()
    audit = metric.describe(final)
    if abs(audit['q_per_measurement']-record['audit']['q_per_measurement']) > 1e-10:
        raise ValueError('saved audit q mismatch')
    if not np.all(final/metric.sigma > 1e-8):
        raise ValueError('endpoint infeasible')
    high = np.asarray(bundle.metric_info['high_COMPASS_indices'], dtype=int)
    if len(high) != 188 or len(set(high)) != 188:
        raise ValueError('diagnostic group mismatch')
    groups = dict(DY=np.arange(743), HERMES=np.arange(743,1087),
                  COMPASS=np.arange(1087,2290), high_COMPASS=high,
                  other_COMPASS=np.setdiff1d(np.arange(1087,2290), high))
    snapshots = {}
    for name, values in [('initial', initial), ('final', final)]:
        residual = metric.data-values
        precision = cho_solve(metric.chol, residual)
        blocks = {}
        for label, indices in groups.items():
            outside = np.setdiff1d(np.arange(metric.n), indices)
            cross_max = float(np.abs(metric.cov[np.ix_(indices, outside)]).max())
            if cross_max != 0:
                raise ValueError('independent block interpretation is invalid')
            q = float(residual[indices]@precision[indices])
            blocks[label] = dict(rows=len(indices), q=q, q_per_block_row=q/len(indices),
                raw_residual_fixed_sigma=describe(residual[indices]/metric.sigma[indices]),
                cross_covariance_max_abs=cross_max)
        snapshots[name] = dict(q_per_measurement=float(residual@precision)/metric.n, blocks=blocks)
    fixed = []
    for i in high:
        meta = read(bundle.file(bundle.index['operators'][i]['metadata']))
        if meta['row']['observation_id'] != bundle.rows[i]['observation_id']:
            raise ValueError('operator row mismatch')
        if meta['denominator'] <= 0 or meta['density_volume'] <= 0:
            raise ValueError('invalid normalization')
        fixed.append(meta['fixed_numerator']/meta['denominator']/meta['density_volume'])
    fixed = np.asarray(fixed)
    sigma = metric.sigma[high]
    train_initial = fixed_split(initial[high], fixed, sigma)
    train_final = fixed_split(final[high], fixed, sigma)
    residual_final = (metric.data[high]-final[high])/sigma
    delta = (final[high]-initial[high])/sigma
    rows = [dict(index=int(i), observation_id=bundle.rows[i]['observation_id'],
        data=float(metric.data[i]), fixed_sigma=float(sigma[j]),
        fixed_matched_contribution=float(fixed[j]),
        initial_prediction=float(initial[i]), final_prediction=float(final[i]),
        initial_trainable_contribution_over_sigma=float(train_initial[j]),
        final_trainable_contribution_over_sigma=float(train_final[j]),
        prediction_change_over_sigma=float(delta[j]),
        final_residual_over_sigma=float(residual_final[j])) for j,i in enumerate(high)]
    reviews = [read(p) for p in sorted(run.glob('diagnostic-review-*.json'))]
    summary = read(run/'diagnostic-summary.json')
    report = dict(schema='tmd-w8-saved-contribution-review-v1', model_calls=0,
        scope='saved endpoints, immutable operator metadata and fixed covariance only',
        run_id=record['run_id'], record_sha256=sha(args.record),
        artifact_sha256=sha(args.archive), verified_archive_files=len(record['files']),
        verified_input_files=len(bundle.index['files']), bundle_identity=bundle.index['identity'],
        snapshots=snapshots, endpoint_audit=audit,
        terminal_gradients=dict(raw_max=float(np.abs(raw).max()),
            penalized_max=float(np.abs(penalized).max()),
            barrier_difference_max=float(np.abs(penalized-raw).max())),
        complete_32_update_intervals=[{k:d[k] for k in ('interval_counters',
            'interval_elapsed_seconds','interval_q_improvement',
            'interval_q_improvement_per_100_forwards')} for d in reviews],
        candidate_verdicts=summary['candidate_verdicts'],
        high_COMPASS=dict(rows=188, underpredicted=int((residual_final>0).sum()),
            fixed_contribution_over_sigma=describe(fixed/sigma),
            initial_trainable_contribution_over_sigma=describe(train_initial),
            final_trainable_contribution_over_sigma=describe(train_final),
            prediction_change_over_sigma=describe(delta),
            final_residual_over_sigma=describe(residual_final),
            final_abs_trainable_below_0_01_sigma=int((np.abs(train_final)<.01).sum()),
            final_q_fraction=snapshots['final']['blocks']['high_COMPASS']['q']/(metric.n*snapshots['final']['q_per_measurement']),
            interpretation='Amplitude decomposition, not local sensitivity or an irreducible residual floor. Fixed means the full fixed matched numerator, not FO alone.',
            row_diagnostics=rows))
    if args.out.exists():
        raise ValueError('refusing to replace an existing review')
    write(args.out, report)
    print(args.out)
    print({k:v for k,v in report['high_COMPASS'].items() if k != 'row_diagnostics'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run','record','archive','bundle','out'):
        parser.add_argument('--'+key, type=Path, required=True)
    review(parser.parse_args())
