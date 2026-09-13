#!/usr/bin/env python3
"""Compare hash-verified published paired calibration evidence; saved-only."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tmdlab.calibration import evidence,decide
from tmdlab.io import write

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('control-run','control-record','adaptive-run','adaptive-record','out'):
        p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args()
    if args.out.exists():raise ValueError('decision output already exists; preserve historical evidence')
    result=decide(evidence(args.control_run,args.control_record),evidence(args.adaptive_run,args.adaptive_record))
    write(args.out,result); print(result['status'],result['selected_policy'])
