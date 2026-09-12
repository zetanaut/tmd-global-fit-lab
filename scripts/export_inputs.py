#!/usr/bin/env python3
"""Owner-side export of immutable operator bytes, fixed metric and saved starts.

Run with the historical pdf-fit interpreter. This only reads the source trees
and writes a NEW destination. No model evaluation, fit, CUDA call or t0 update.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[key] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tmdlab.io import sha, read, write, digest, SOURCE_ID, METRIC_ID

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--foundation", required=True, type=Path)
    p.add_argument("--manager", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    root, manager, out = args.foundation.resolve(), args.manager.resolve(), args.out.resolve()
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(manager):
        raise ValueError("new nonoverlapping output directory required")
    sys.path[:0] = [str(root), str(root/"src")]
    import numpy as np
    from work.global_residual_assessment_2026_09_11 import assess as a
    pins = a.Pins()
    metric, snapshot, reference = a.load_metric(pins)
    source = root/"work/haps_global_operators_2026_09_10/manifests_v1/two_scale.json"
    manifest = read(source)
    if manifest["identity"] != SOURCE_ID or digest({k:v for k,v in manifest.items() if k != "identity"}) != SOURCE_ID:
        raise ValueError("wrong source manifest")
    out.mkdir(parents=True)
    files, operators, checkpoints = {}, [], {}
    def register(relative):
        path = out/relative
        files[relative] = dict(bytes=path.stat().st_size, sha256=sha(path))
    def copy(source, relative, expected=None):
        source = Path(source)
        before = sha(source)
        if expected is not None and before != expected:
            raise ValueError(f"source pin failed: {source}")
        dest = out/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        register(relative)
        if files[relative]["sha256"] != before or sha(source) != before:
            raise ValueError("copy/source changed")
    copy(source, "source-manifest.json")
    for i, ref in enumerate(manifest["references"]):
        src = Path(ref["path"])
        src = src/"operator.json" if src.is_dir() else src
        name = f"operators/{i:04d}"
        copy(src,name+"/operator.json",ref["json_sha256"])
        copy(src.with_name("operator.npz"),name+"/operator.npz",ref["npz_sha256"])
        operators.append(dict(metadata=name+"/operator.json",arrays=name+"/operator.npz"))
        if i%250 == 0:
            print(f"exported {i+1}/2290 operators", flush=True)
    saved = a.load_archive(a.SNAPSHOT.with_suffix(".npz"),snapshot["arrays"]["sha256"],pins)
    old = pins.signed(a.OLD_SNAPSHOT,a.OLD_SNAPSHOT_ID)
    regions = pins.signed(a.HERE/"completed_stage1_regions_v1/regions.json")
    high = next(g["indices"] for g in regions["groups"][0]["groups"] if g["experiment"] == "COMPASS" and g["source_region"] == "whole_outer_support_at_or_above_threshold")
    np.savez_compressed(out/"metric.npz",data=metric.data,covariance=a.effective_covariance(metric),reference=reference,DY_diagonal=saved["DY_diagonal"],DY_responses=saved["DY_responses"],U=metric.U)
    register("metric.npz")
    write(out/"metric.json",dict(metric_identity=METRIC_ID,ids=list(metric.ids),units=list(metric.units),DY_nuisance_ids=old["DY_nuisance_ids"],high_COMPASS_indices=high,residual_convention="(data-prediction)/sqrt(diag(C_eff)); correlated diagnostic",source_snapshots={Path(path).name+"-"+str(i):dict(sha256=h) for i,(path,h) in enumerate(pins.files.items())}))
    register("metric.json")
    specs = {
        "anchor-w8":(root/"work/controlled_film_matching_2026_09_10/nested_seed11_v1/final.npz",8,None),
        "p0-w8-083":(manager/"gpu_film_refinement_2026_09_12_v1/film_w8_d1_c12_v1/S01/checkpoint_083.npz",8,"d195ecee17317e5164872dfcf096040ba69542ef1b8852f6995d28232a0ed075"),
        "p0-w24-064":(manager/"gpu_film_comparable_continuation_2026_09_12_v1/attempt_001/film_w24_d1_c12_v1/S00/checkpoint_064.npz",24,"549a6d01fa45e956f3651c70f8b5475ef991e41475d7fec6b6de39087d0483e2"),
        "p0-w16-096":(manager/"gpu_film_refinement_2026_09_12_v1/film_w16_d1_c12_v1/S02/final.npz",16,"cf634461ee7bddae3d76ca90cc03e339bd5b6b272cbb26fb3b5bd7eeb0285843")}
    from tmdlab.models import build,Config,schema
    for name,(path,width,expected) in specs.items():
        relative = "checkpoints/"+name+".npz"
        copy(path,relative,expected)
        with np.load(path,allow_pickle=False) as z:
            values,theta = z["values"],z["theta"]
            q = float((metric.data-values)@metric.solve(metric.data-values)/2290)
            if values.shape != (2290,) or theta.size != {8:1570,16:2882,24:4706}[width] or not np.isfinite(theta).all() or not (values > 0).all():
                raise ValueError("invalid declared positive checkpoint")
        checkpoints[name] = dict(path=relative,model={"width":width,"depth":1},parameters=int(theta.size),parameter_schema=schema(build(Config(width=width))),q_per_measurement=q,optimizer_history="not_available_reset_must_be_declared")
    for relative in ("work/film_architecture_2026_09_10/model.py","work/film_nested_architecture_2026_09_10/model.py","work/global_device_evaluator_2026_09_11/engine.py","work/film_operator_adapter_2026_09_10/adapter.py","work/global_residual_assessment_2026_09_11/assess.py"):
        copy(root/relative,"historical-source/"+relative)
    for i,path in enumerate(pins.files):
        copy(path,"historical-metric/"+str(i)+"-"+Path(path).name,pins.files[path])
    pins.recheck()
    body = dict(schema="tmd-portable-inputs-v1",source_identity=SOURCE_ID,metric_identity=METRIC_ID,source_manifest_file_sha256=files["source-manifest.json"]["sha256"],files=files,operators=operators,checkpoints=checkpoints,scientific_arrays_changed=False,transport_paths_are_new=True)
    write(out/"bundle.json",dict(body,identity=digest(body)))
    print(json.dumps(dict(bundle_identity=digest(body),files=len(files),bytes=sum(f["bytes"] for f in files.values()),model_evaluations=0,gpu_calls=0),indent=2))

if __name__ == "__main__":
    main()
