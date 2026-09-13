#!/usr/bin/env python3
"""Saved-only, hash-verified paired calibration tables and learning curves."""
import argparse
import csv
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmdlab.calibration import evidence, decide
from tmdlab.io import read, write


def rows(run, record_path, arm):
    run = Path(run)
    record = read(record_path)
    result = []
    for path in sorted(run.glob('accepted-*.json')):
        step = read(path)
        counts = step['trajectory_counters']
        with np.load(run/path.name.replace('accepted-', 'checkpoint-').replace('.json', '.npz'), allow_pickle=False) as checkpoint:
            gradient_max = float(np.max(np.abs(checkpoint['penalized_gradient'])))
        result.append(dict(arm=arm, run_id=record['run_id'],
            cumulative_updates=counts['accepted_updates'],
            new_forwards=step['forwards'], new_full_calls=step['full_calls'],
            cumulative_forwards=counts['forwards'], cumulative_full_calls=counts['full_calls'],
            new_infeasible=step['infeasible_trials'], new_rejections=step['line_search_rejections'],
            model_seconds=step['elapsed_seconds'],
            cumulative_model_seconds=record['model_seconds_before']+step['elapsed_seconds'],
            q_per_measurement=step['q_per_measurement'], objective=step['objective'],
            alpha=step['alpha'], mu=step['mu'],
            penalized_gradient_max=gradient_max))
    return result


def learning_svg(data):
    """Plot saved accepted states; endpoint-only calls are in the separate ledger."""
    panels = [('cumulative_updates', 'Cumulative P1 accepted updates'),
              ('new_forwards', 'New charged forwards at accepted state'),
              ('model_seconds', 'Segment model seconds at accepted state')]
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="350" viewBox="0 0 1200 350">',
             '<rect width="1200" height="350" fill="white"/>',
             '<g font-family="sans-serif" font-size="12" fill="#222">',
             '<text x="25" y="22">Width8 paired calibration: q/N at saved accepted states (lower is better)</text>',
             '<text x="25" y="333">Unit: blue. Adaptive: orange. Preflight/rejections charged; final raw-gradient call is in endpoint ledger, not an accepted-state point.</text>']
    qmin = min(r['q_per_measurement'] for r in data)
    qmax = max(r['q_per_measurement'] for r in data)
    pad = max((qmax-qmin)*.08, 1e-8)
    qmin -= pad
    qmax += pad
    for panel, (key, label) in enumerate(panels):
        left, top, width, height = panel*400+68, 52, 308, 225
        xmin = min(r[key] for r in data)
        xmax = max(r[key] for r in data)
        def x(value): return left+(value-xmin)/max(xmax-xmin, 1e-12)*width
        def y(value): return top+height-(value-qmin)/(qmax-qmin)*height
        for i in range(5):
            q = qmin+(qmax-qmin)*i/4
            xv = xmin+(xmax-xmin)*i/4
            lines.extend([f'<path d="M {left} {y(q):.2f} h {width}" stroke="#ddd"/>',
                f'<text x="{left-6}" y="{y(q)+4:.2f}" text-anchor="end">{q:.4f}</text>',
                f'<text x="{x(xv):.2f}" y="{top+height+20}" text-anchor="middle">{xv:.0f}</text>'])
        lines.append(f'<text x="{left+width/2}" y="315" text-anchor="middle">{label}</text>')
        for arm, color in [('unit', '#1764b4'), ('adaptive', '#c85b0b')]:
            points = ' '.join(f"{x(r[key]):.2f},{y(r['q_per_measurement']):.2f}" for r in data if r['arm']==arm)
            lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
    return '\n'.join(lines+['</g></svg>'])+'\n'


def main(args):
    control = evidence(args.control_run, args.control_record)
    adaptive = evidence(args.adaptive_run, args.adaptive_record)
    decision = decide(control, adaptive)
    if decision['status'] != 'comparable':
        raise ValueError('complete common milestone required for this report')
    args.out.mkdir(parents=True, exist_ok=False)
    data = rows(args.control_run, args.control_record, 'unit')+rows(args.adaptive_run, args.adaptive_record, 'adaptive')
    with (args.out/'accepted-learning-curves.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    (args.out/'accepted-learning-curves.svg').write_text(learning_svg(data))
    write(args.out/'decision.json', decision)
    endpoints = {}
    for arm, path in [('unit', args.control_record), ('adaptive', args.adaptive_record)]:
        record = read(path)
        endpoints[arm] = {key: record[key] for key in
            ('run_id', 'identity', 'counters', 'trajectory_counters', 'model_seconds_before',
             'trajectory_model_seconds', 'audit', 'plateau', 'supervisor', 'artifact')}
    write(args.out/'endpoint-ledger-and-diagnostics.json', endpoints)
    print(decision['status'], decision['selected_policy'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('control-run', 'control-record', 'adaptive-run', 'adaptive-record', 'out'):
        parser.add_argument('--'+key, type=Path, required=True)
    main(parser.parse_args())
