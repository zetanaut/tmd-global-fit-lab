#!/usr/bin/env python3
"""Bounded HERMES K- comparison: NNFF10 versus HAPS-KaFF10.

Theory-only diagnostic.  It evaluates the 19 already-identified PV17 K- rows
with the current regional matching code and Gaussian NP control.  No fit or
operator replacement is performed.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = Path('/home/dustin/Documents/Codex/2026-09-03/i-x20/work/global_fit_foundation')
INDICES = (84,108,114,121,149,155,156,162,163,170,840,864,870,877,905,912,918,919,925)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', type=Path, default=ROOT/'run-output/historical-closure-baseline-20260915/pv17-row-manifest.jsonl')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists(): raise ValueError('refuse to overwrite diagnostic')
    sys.path[:0] = [str(ROOT), str(FOUNDATION), str(FOUNDATION/'src')]
    import scripts.run_pv17_sidis_point_pilot as pilot
    from work.regional_matching.service import RegionalConfig, RegionalService
    from work.alternative_kaon_ff_2026_09_10.inputs import bind
    rows = [json.loads(line) for line in args.manifest.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r.get('selected_index') in INDICES]
    if tuple(sorted(r['selected_index'] for r in rows)) != INDICES: raise ValueError('19-row manifest mismatch')
    family_path = FOUNDATION/'work/alternative_kaon_ff_2026_09_10/inputs/HAPS_KaFF10_nnlo.json'
    family = json.loads(family_path.read_text())
    results = {}
    for label, selected in (('NNFF10_nnlo', None), ('HAPS_KaFF10_nnlo', family)):
        with bind(selected):
            services = {}
            for row in rows:
                key = row['target']
                if key not in services:
                    target = pilot.TARGET_MAP[key]
                    services[key] = RegionalService(RegionalConfig(target=target, hadron='K-', pdf_xmin=.003, ff_zmin=.2))
            vals = []
            try:
                for row in rows:
                    scalar = pilot.point_density(services[row['target']], row, b_order=8)
                    vals.append({'selected_index': row['selected_index'], 'source_id': row['source_id'],
                        'target': row['target'], 'transition_weight': scalar['transition_weight'],
                        'prediction': scalar['multiplicity_per_dPhT'], 'pieces': scalar['pieces_per_dqT2']})
            finally:
                for service in services.values(): service.close()
        results[label] = vals
    summary = {k: {'negative': sum(v['prediction'] < 0 for v in vals), 'minimum': min(v['prediction'] for v in vals),
                   'positive': sum(v['prediction'] > 0 for v in vals)} for k, vals in results.items()}
    payload = {'schema':'pv17-hermes-kminus-ff-family-diagnostic-v1', 'indices':list(INDICES),
        'scope':{'theory_only':True,'observable':'current PV17 dM/dPhT','NP':'Gaussian exp(-b^2/4)','b_order':8,
                 'production_changed':False,'fit_run':False}, 'families':results, 'summary':summary,
        'inputs':{'manifest_sha256':sha(args.manifest),'haps_input_sha256':sha(family_path),
                  'producer_sha256':sha(Path(__file__))}}
    payload['identity'] = hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'identity':payload['identity'],'summary':summary}), flush=True)

if __name__ == '__main__': main()
