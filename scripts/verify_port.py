#!/usr/bin/env python3
"""Owner-side CPU comparison with the original model/evaluator (no fit)."""
import argparse
import os
from pathlib import Path
import sys
for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"): os.environ[k]="1"
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from tmdlab.bundle import Bundle
from tmdlab.models import build,Config,put,schema
from tmdlab.engine import Engine
from tmdlab.io import write,sha,utc

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--foundation",type=Path,required=True);p.add_argument("--bundle",required=True);p.add_argument("--out",required=True)
    args=p.parse_args();torch.set_num_threads(1)
    sys.path[:0]=[str(args.foundation),str(args.foundation/"src")]
    from work.film_nested_architecture_2026_09_10.model import build_model,NestedConfig
    from work.global_device_evaluator_2026_09_11.engine import DeviceEngine
    bundle=Bundle(args.bundle); checks=[]
    indices=[0,100,328,743,1087,2289]
    cot=np.array([.1,-.2,.3,-.4,.5,-.6])
    for name in ("anchor-w8","p0-w16-096","p0-w24-064"):
        entry,saved=bundle.checkpoint(name);width=entry["model"]["width"]
        new=build(Config(width=width));old=build_model(NestedConfig(width=width))
        if schema(new)!=schema(old): raise ValueError("parameter schemas differ")
        put(old,saved["theta"]);put(new,saved["theta"])
        reference=DeviceEngine(old,bundle.manifest,device="cpu",indices=indices,max_evaluations=4)
        portable=Engine(new,bundle,"cpu",indices=indices)
        try:
            expected=reference.evaluate(saved["theta"],cotangents=cot)
            values,g=portable.evaluate(saved["theta"],cot)
            with np.load(bundle.file("metric.npz"),allow_pickle=False) as f: sigma=np.sqrt(np.diag(f["covariance"]))
            pred=float(np.max(np.abs(values-expected["values"])/sigma[indices]))
            grad=float(np.max(np.abs(g-expected["gradient"])))
            saved_error=float(np.max(np.abs(values-saved["values"][indices])/sigma[indices]))
            if pred>1e-7 or grad>1e-7 or saved_error>1e-7: raise ValueError("port equivalence gate failed")
            checks.append(dict(checkpoint=name,width=width,prediction_error_fixed_sigma=pred,gradient_absolute_error=grad,saved_prediction_error_fixed_sigma=saved_error,parameters=saved["theta"].size))
        finally: portable.close();reference.close()
    source_dir=Path(__file__).resolve().parents[1]/"tmdlab"
    write(args.out,dict(schema="tmd-port-equivalence-v1",passed=True,generated_utc=utc(),scope="six measured rows, three widths; forward and fixed-cotangent VJP; not a full2290 GPU certificate",indices=indices,checks=checks,bundle_identity=bundle.index["identity"],GPU_calls=0,optimizer_updates=0,source_pins={"tmdlab/"+name:sha(source_dir/name) for name in ("models.py","engine.py","bundle.py","metric.py","io.py")}))
    print(args.out)

if __name__=="__main__": main()
