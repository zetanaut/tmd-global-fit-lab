"""Create small immutable Git records from a run and a published artifact URI."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from .io import read,write,sha,digest,utc,SOURCE_ID,METRIC_ID

def validate_record(r):
    if r["schema"]!="tmd-result-v1" or r["identity"]!=digest({k:v for k,v in r.items() if k!="identity"}): raise ValueError("result identity mismatch")
    if r["source_identity"]!=SOURCE_ID or r["metric_identity"]!=METRIC_ID: raise ValueError("result scientific identity mismatch")
    if r["status"] not in ("completed","partial","failed"): raise ValueError("invalid result status")
    if not re.fullmatch(r"[a-z0-9-]+",r["run_id"]) or not re.fullmatch(r"[0-9a-f]{40,64}",r["code_commit"]): raise ValueError("run/code identity missing")
    if r["status"]=="completed" and (r["worker_status"]!="completed" or not r["audit"] or not r["audit"].get("passed") or r["supervisor"]["stop_reason"] is not None): raise ValueError("completion without worker/audit/supervisor evidence")
    url=urlsplit(r["artifact"]["url"])
    if url.scheme!="https" or url.netloc!="github.com" or not re.fullmatch(r"/zetanaut/tmd-global-fit-lab/releases/download/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+",url.path) or url.query or url.fragment or not re.fullmatch(r"[0-9a-f]{64}",r["artifact"]["sha256"]): raise ValueError("exact immutable artifact location/digest required")
    if r.get("production_selected") is not False: raise ValueError("no production selection in this study")
    return r

def collect(args):
    run=Path(args.run); launch=read(run/"launch.json"); trial=read(run/"trial.json")
    if any(p.is_symlink() for p in run.rglob("*")): raise ValueError("run archive cannot contain symlinks to other trees")
    supervisor=read(run/"supervisor.json")
    paired=trial.get('execution_policy')=='paired-feasibility-v1'
    worker_root=run/"worker" if paired else run
    summary_path=worker_root/"worker-summary.json"
    summary_missing=not summary_path.is_file()
    if summary_missing:
        # A declared supervisor deadline can reap a worker while it is already
        # handling the evaluator deadline, before the worker's final summary is
        # written.  Preserve that absence, but do not replace the authoritative
        # supervisor reason with a misleading generic missing-summary label.
        counters_path=worker_root/"counters.json"
        worker=dict(status="partial" if supervisor.get("stop_reason") else "failed",
            stop_reason=supervisor.get("stop_reason") or "worker_killed_or_missing_summary",
            counters=read(counters_path) if counters_path.is_file() else None,
            plateau=None,optimizer_history_reset=None,summary_missing=True)
    else:
        worker=read(summary_path)
    audit=read(run/"audit.json") if (run/"audit.json").is_file() else None
    status=worker["status"]
    if supervisor["stop_reason"] is not None or not audit or not audit.get("passed"):
        status="partial" if audit and audit.get("passed") else "failed"
    record=dict(schema="tmd-result-v1",run_id=launch["run_id"],trial_id=launch["trial_id"],trial_sha256=launch["trial_sha256"],code_commit=launch["code_commit"],bundle_identity=launch["bundle_identity"],source_identity=trial["source_identity"],metric_identity=trial["metric_identity"],kind=trial["kind"],phase=trial["phase"],model=trial["model"],start_checkpoint=trial["start_checkpoint"],status=status,worker_status=worker["status"],stop_reason=worker.get("stop_reason"),counters=worker.get("counters"),plateau=worker.get("plateau"),optimizer_history_reset=worker.get("optimizer_history_reset"),worker_summary_missing=summary_missing,audit=audit,supervisor=supervisor,hardware=launch["device"],slurm=launch["slurm"],claim=launch["claim"],artifact={"url":args.artifact_url,"sha256":sha(args.artifact),"bytes":Path(args.artifact).stat().st_size},files={str(p.relative_to(run)):{"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(run.rglob("*")) if p.is_file()},recorded_utc=utc(),production_selected=False)
    if trial.get('execution_policy') in ('p1-resume-v1','p1-resume-v2'):
        from .restart import recover_native,COUNTERS
        reconciled=recover_native(run,record) if (run/'restart.npz').is_file() and audit and audit.get('passed') else None
        ledger=read(run/'counters.json') if (run/'counters.json').is_file() else {}
        record.update(trajectory_counters=dict(zip(COUNTERS,map(int,reconciled['counters']))) if reconciled is not None else ledger.get('trajectory_counters'),
            trajectory_budget=trial['trajectory_budget'],
            model_seconds_before=launch['model_seconds_before'],
            trajectory_model_seconds=launch['model_seconds_before']+supervisor['elapsed_seconds'])
    record["identity"]=digest(record); validate_record(record)
    dest=Path(args.out)/record["trial_id"]/f"{record['run_id']}.json"
    if dest.exists(): raise ValueError("immutable result already exists")
    write(dest,record); print(dest)

def render(root):
    records=[validate_record(read(p)) for p in sorted((root/"results").glob("*/*.json"))]
    lines=["# Experiment results","","Generated from immutable result JSON; rerun `python -m tmdlab.results report`.","","A completed schedule is not convergence. Diagnostic/replay trials are not fits. No production model is selected.","","| Trial | Status | Kind | q/N | Updates | Plateau | Artifact |","|---|---|---|---:|---:|---|---|"]
    for r in records:
        q="—" if not r["audit"] or "q_per_measurement" not in r["audit"] else f"{r['audit']['q_per_measurement']:.9f}"
        n=(r["counters"] or {}).get("accepted_updates","—")
        p="passed" if r["plateau"] and r["plateau"].get("passed") else "not established"
        lines.append(f"| {r['trial_id']} | {r['status']} | {r['kind']} | {q} | {n} | {p} | [download]({r['artifact']['url']}) |")
    if not records: lines.extend(["","No portable trial results have been published. Historical results are separately qualified in `docs/BASELINE_RESULTS.md`."])
    return "\n".join(lines)+"\n"

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="command",required=True)
    c=sub.add_parser("collect");c.add_argument("--run",required=True);c.add_argument("--artifact",required=True);c.add_argument("--artifact-url",required=True);c.add_argument("--out",default="results")
    r=sub.add_parser("report");r.add_argument("--check",action="store_true")
    args=p.parse_args()
    if args.command=="collect": collect(args)
    else:
        root=Path.cwd();content=render(root);dest=root/"RESULTS.md"
        if args.check:
            if not dest.is_file() or dest.read_text()!=content: raise SystemExit("RESULTS.md is stale")
        else: dest.write_text(content)
