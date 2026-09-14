#!/usr/bin/env python3
"""Import complete legacy P1 accepted-state chains without any model calls."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from tmdlab.io import read,write,sha,digest
from tmdlab.bundle import Bundle
from tmdlab.restart import reconstruct_v1,recover_native,elapsed_before,ALGORITHM,COUNTERS
from tmdlab.results import validate_record
from tmdlab.contracts import RESUME_TRAJECTORY_LIMITS

def main(args):
    root=Path.cwd().resolve(); run=Path(args.run).resolve(); record_path=Path(args.record).resolve()
    record=validate_record(read(record_path)); trial=read(run/'trial.json')
    if sha(args.archive)!=record['artifact']['sha256']:
        raise ValueError('published archive digest mismatch')
    native=trial.get('execution_policy') in RESUME_TRAJECTORY_LIMITS
    a=recover_native(run,record) if native else reconstruct_v1(run,record)
    bundle=Bundle(args.bundle)
    if native:
        parent=read(root/'restarts'/(trial['start_checkpoint'][8:]+'.json'))
    elif trial['start_checkpoint'].startswith('overlay:'):
        parent=read(root/'checkpoints'/ (trial['start_checkpoint'][8:]+'.json'))
    else:
        parent,_=bundle.checkpoint(trial['start_checkpoint'])
    pending=root/'checkpoint-objects'/'restart-import.pending.npz'
    if pending.exists(): raise ValueError('unfinished import already present')
    np.savez_compressed(pending,**a); hashed=sha(pending)
    dest=pending.parent/(hashed+'.npz')
    if dest.exists():
        if sha(dest)!=hashed: raise ValueError('immutable restart object collision')
        pending.unlink()
    else:
        pending.rename(dest)
    m=dict(schema='tmd-optimizer-restart-v1',algorithm=ALGORITHM,
        model=trial['model'],parameters=a['theta'].size,parameter_schema=parent['parameter_schema'],
        source_identity=trial['source_identity'],metric_identity=trial['metric_identity'],bundle_identity=trial['bundle_identity'],
        parent_run_id=record['run_id'],parent_record=dict(path=str(record_path.relative_to(root)),sha256=sha(record_path)),
        artifact=record['artifact'],q_per_measurement=record['audit']['q_per_measurement'],mu=float(a['mu']),
        counters=dict(zip(COUNTERS,map(int,a['counters']))),
        model_seconds_before=(elapsed_before(root,parent) if native else 0.)+record['supervisor']['elapsed_seconds'],
        reconstruction=dict(method='atomic-native-state-and-dispatch-ledger' if native else 'all-accepted-theta-and-penalized-gradient-chain',
            accepted_transition_absolute_tolerance=1e-12,interrupted_calls_remain_charged=True,
            continuation_scope='accepted-state-boundary; unfinished line search is replayed with additional cost'),
        object=dict(path=str(dest.relative_to(root)),sha256=hashed,bytes=dest.stat().st_size))
    m['identity']=digest(m)
    path=root/'restarts'/(m['identity']+'.json')
    if path.exists(): raise ValueError('immutable restart manifest already present')
    write(path,m); print(path)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','record','archive','bundle'): p.add_argument('--'+key,required=True,type=Path)
    main(p.parse_args())
