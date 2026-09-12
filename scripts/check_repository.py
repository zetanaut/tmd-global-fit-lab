#!/usr/bin/env python3
"""CPU-only structural checks; no model calls, CUDA, network or large assets."""
import argparse
import ast
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tmdlab.io import read
from tmdlab.contracts import validate_trial
from tmdlab.results import validate_record,render

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--base");args=p.parse_args()
    root=Path.cwd();lock=read(root/"data/baseline-v1.json")
    trials=list((root/"trials").glob("*.json"))
    for path in trials:
        t=validate_trial(read(path),require_ready=False)
        if path.stem!=t["trial_id"] or t["bundle_identity"]!=lock["bundle_identity"]:raise ValueError("trial filename/bundle mismatch")
    for path in (root/"results").glob("*/*.json"):
        r=validate_record(read(path))
        if path.stem!=r["run_id"] or path.parent.name!=r["trial_id"]:raise ValueError("result path mismatch")
    for directory in ("tmdlab","scripts","tests"):
        for path in (root/directory).glob("*.py"):ast.parse(path.read_text(),filename=str(path))
    if (root/"RESULTS.md").read_text()!=render(root):raise ValueError("RESULTS.md needs regeneration")
    if args.base:
        changes=subprocess.check_output(["git","diff","--name-status",args.base,"HEAD","--","results","trials","data"],text=True)
        for line in changes.splitlines():
            mode,path=line.split("\t",1)
            if mode!="A" and (path.startswith("results/") or path.startswith("trials/")):raise ValueError("immutable result/trial modified or deleted: "+path)
    print(f"validated {len(trials)} trial specs, result records, generated table and Python syntax")

