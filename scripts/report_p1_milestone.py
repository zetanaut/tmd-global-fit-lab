#!/usr/bin/env python3
"""Review hash-bound P1 segments and their remaining common-milestone work.

Saved arrays and receipts only. No observable or gradient evaluation.
"""
import argparse
import csv
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmdlab.io import read, write, sha
from tmdlab.restart import recover_native, COUNTERS
from tmdlab.results import validate_record


def review(root, run, record_path):
    record = validate_record(read(record_path))
    restart = recover_native(run, record)
    trial = read(run/'trial.json')
    parent = read(root/'restarts'/(trial['start_checkpoint'][8:]+'.json'))
    steps = [read(path) for path in sorted(run.glob('accepted-*.json'))]
    if len(steps) != record['counters']['accepted_updates']:
        raise ValueError('accepted chain length differs from terminal counters')
    for i, step in enumerate(steps, 1):
        if step['accepted_updates'] != i or step['trajectory_counters']['accepted_updates'] != parent['counters']['accepted_updates']+i:
            raise ValueError('accepted trajectory index mismatch')
    if steps[-1]['q_per_measurement'] != record['audit']['q_per_measurement']:
        raise ValueError('last accepted state differs from audited score')
    with np.load(run/'restart.npz', allow_pickle=False) as archive:
        committed_counts = dict(zip(COUNTERS, map(int, archive['counters'])))
    charged_counts = dict(zip(COUNTERS, map(int, restart['counters'])))
    endpoint = dict(width=trial['model']['width'], run_id=record['run_id'], result_identity=record['identity'],
        status=record['status'], parent_q_per_measurement=parent['q_per_measurement'],
        endpoint_q_per_measurement=record['audit']['q_per_measurement'],
        q_improvement=parent['q_per_measurement']-record['audit']['q_per_measurement'],
        initial_accepted_updates=parent['counters']['accepted_updates'],
        charged_counters=charged_counts, committed_restart_counters=committed_counts,
        additional_charges_after_restart={k:charged_counts[k]-committed_counts[k] for k in COUNTERS},
        remaining_to_96=96-charged_counts['accepted_updates'],
        remaining_budget=dict(forwards=trial['trajectory_budget']['forwards']-charged_counts['forwards'],
            full_calls=trial['trajectory_budget']['full_calls']-charged_counts['full_calls'],
            model_seconds=trial['trajectory_budget']['model_seconds']-record['trajectory_model_seconds']),
        segment_model_seconds=record['supervisor']['elapsed_seconds'],
        trajectory_model_seconds=record['trajectory_model_seconds'],
        audit=record['audit'], plateau=record['plateau'], artifact=record['artifact'],
        stop_reason=record['supervisor']['stop_reason'], optimizer_history_preserved=True)
    rows = []
    for step in steps:
        rows.append(dict(width=trial['model']['width'], run_id=record['run_id'],
            cumulative_accepted_updates=step['trajectory_counters']['accepted_updates'],
            cumulative_forwards=step['trajectory_counters']['forwards'],
            cumulative_full_calls=step['trajectory_counters']['full_calls'],
            cumulative_model_seconds=record['model_seconds_before']+step['elapsed_seconds'],
            q_per_measurement=step['q_per_measurement'], alpha=step['alpha'],
            new_infeasible_trials=step['infeasible_trials'], new_line_search_rejections=step['line_search_rejections'],
            plateau_passed=step['plateau']['passed']))
    return endpoint, rows


def main(args):
    root=Path.cwd().resolve()
    endpoints=[]; rows=[]
    for run in args.run:
        launch=read(run/'launch.json')
        path=root/'results'/launch['trial_id']/(launch['run_id']+'.json')
        endpoint, trajectory=review(root,run,path)
        endpoints.append(endpoint); rows.extend(trajectory)
    if sorted(item['width'] for item in endpoints)!=[8,16,24]:
        raise ValueError('exactly one segment per width required')
    args.out.mkdir(parents=True,exist_ok=False)
    with (args.out/'accepted-learning-curves.csv').open('x',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    write(args.out/'review.json',dict(schema='tmd-p1-milestone-review-v1',model_calls=0,endpoints=endpoints,
        decision='repair progress-metadata monitoring; preserve unit-backtracking and verified optimizer states; complete remaining common96 allowances',
        architecture_winner_established=False, convergence_established=False,
        record_hashes={str(p.relative_to(root)):sha(p) for p in sorted((root/'results').glob('continuation-*-p1-m96-a01/*.json'))}))
    print(args.out/'review.json')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,action='append',required=True)
    parser.add_argument('--out',type=Path,required=True)
    main(parser.parse_args())
