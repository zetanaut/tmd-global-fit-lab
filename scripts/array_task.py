#!/usr/bin/env python3
"""Read a preregistered task/claim mapping; no shell-evaluated commands in JSON."""
import argparse
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tmdlab.io import read,within
from tmdlab.contracts import validate_trial

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--tasks",required=True);p.add_argument("--index",type=int,required=True);p.add_argument("--bundle",required=True);p.add_argument("--output",required=True);p.add_argument("--device",required=True);args=p.parse_args()
    tasks=read(args.tasks)
    if not 0<=args.index<len(tasks):raise ValueError("array index outside exact task list")
    task=tasks[args.index];trial=within(Path.cwd(),task["trial"]);spec=validate_trial(read(trial))
    claim=Path(task["claim"]).resolve()
    out=Path(args.output).resolve()/spec["trial_id"]
    os.execv(sys.executable,[sys.executable,"-m","tmdlab.run","--trial",str(trial),"--bundle",str(Path(args.bundle).resolve()),"--out",str(out),"--device",args.device,"--claim",str(claim)])
