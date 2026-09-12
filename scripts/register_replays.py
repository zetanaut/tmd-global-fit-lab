#!/usr/bin/env python3
"""Generate the six explicitly preregistered portability gates from a bundle lock."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tmdlab.io import read,write,SOURCE_ID,METRIC_ID

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--lock",default="data/baseline-v1.json");args=p.parse_args()
    lock=read(args.lock)
    for device in ("cpu","gpu"):
        for width,start in ((8,"anchor-w8"),(16,"p0-w16-096"),(24,"p0-w24-064")):
            trial=dict(schema="tmd-trial-v1",trial_id=f"replay-w{width}-{device}-a01",status="ready",phase="PORT",kind="replay",hypothesis="The portable evaluator preserves the exact saved predictions and derivatives under the fixed scientific contract.",source_identity=SOURCE_ID,metric_identity=METRIC_ID,bundle_identity=lock["bundle_identity"],model_family="nested-film-v1",model={"width":width,"depth":1},start_checkpoint=start,seed=2026091200+width,dtype="float64",rows=2290,execution_class=device,phases=[],budget=dict(segment_seconds=1800,total_seconds=3600,full_calls=240,forwards=600,accepted_updates=96,cache_gib=12,gpu_gib=20,rss_gib=48,host_available_gib=8,cpu_threads=1),claim_required=True,production_selection=False)
            dest=Path("trials")/(trial["trial_id"]+".json")
            if dest.exists():raise ValueError("immutable trial already exists")
            write(dest,trial)
