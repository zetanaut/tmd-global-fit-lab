#!/usr/bin/env python3
"""CPU-only structural checks; no model calls, CUDA, network or large assets."""
import argparse
import ast
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tmdlab.io import read,sha,within
from tmdlab.contracts import validate_trial
from tmdlab.results import validate_record,render
from tmdlab.checkpoints import manifest,validate_binding

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--base");args=p.parse_args()
    root=Path.cwd();lock=read(root/"data/baseline-v1.json")
    trials=list((root/"trials").glob("*.json"))
    for path in trials:
        t=validate_trial(read(path),require_ready=False)
        if path.stem!=t["trial_id"] or t["bundle_identity"]!=lock["bundle_identity"]:raise ValueError("trial filename/bundle mismatch")
        if t["start_checkpoint"].startswith("overlay:"):
            validate_binding(t,manifest(root,t["start_checkpoint"][8:]))
    for path in (root/"checkpoints").glob("*.json"):
        m=manifest(root,path.stem)
        if m["bundle_identity"]!=lock["bundle_identity"]:raise ValueError("overlay baseline changed")
        for ref in (m["object"],m["evidence"],m["terminal_receipt"]):
            artifact=within(root,ref["path"])
            if sha(artifact)!=ref["sha256"] or "bytes" in ref and artifact.stat().st_size!=ref["bytes"]:
                raise ValueError("overlay artifact hash/size mismatch")
    for path in (root/"evidence").glob("*/index.json"):
        for ref in read(path)["records"].values():
            if sha(within(root,ref["path"]))!=ref["sha256"]:raise ValueError("historical evidence changed")
    for path in (root/"results").glob("*/*.json"):
        r=validate_record(read(path))
        if path.stem!=r["run_id"] or path.parent.name!=r["trial_id"]:raise ValueError("result path mismatch")
    for directory in ("tmdlab","scripts","tests"):
        for path in (root/directory).glob("*.py"):ast.parse(path.read_text(),filename=str(path))
    if (root/"RESULTS.md").read_text()!=render(root):raise ValueError("RESULTS.md needs regeneration")
    if args.base:
        changes=subprocess.check_output(["git","diff","--no-renames","--name-status",args.base,"HEAD","--","results","trials","data","checkpoints","checkpoint-objects","evidence"],text=True)
        for line in changes.splitlines():
            mode,path=line.split("\t",1)
            if mode!="A" and (path.startswith(("results/","trials/","checkpoints/","checkpoint-objects/","evidence/")) or path=="data/baseline-v1.json"):raise ValueError("immutable record/input modified or deleted: "+path)
    print(f"validated {len(trials)} trial specs, result records, generated table and Python syntax")
