"""Saved-only endpoint audit, independent of optimizer success and GPU runtime."""
import argparse
from pathlib import Path
import numpy as np
from .bundle import Bundle
from .metric import Metric
from .io import read,write,sha,utc
from .restart import validate_arrays

def endpoint_arrays(out):
    """Choose the atomic restart if KILL left a legacy last-file behind."""
    out=Path(out); path=out/'last.npz'; arrays=None
    if path.is_file():
        with np.load(path,allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
    trial_path=out/'trial.json'
    native=trial_path.is_file() and read(trial_path).get('execution_policy')=='p1-resume-v1'
    restart=out/'restart.npz'
    if native and restart.is_file():
        with np.load(restart,allow_pickle=False) as z:saved={k:z[k].copy() for k in z.files}
        validate_arrays(saved,saved['theta'].size)
        if arrays is None or any(not np.array_equal(arrays.get(k),saved[k]) for k in ('theta','values','penalized_gradient')):
            return restart,{k:saved[k] for k in ('theta','values','penalized_gradient')}
    return path,arrays

def audit(bundle_dir,out):
    out=Path(out); bundle=Bundle(bundle_dir); metric=Metric(bundle)
    path,arrays=endpoint_arrays(out)
    if arrays is None:
        result=dict(schema="tmd-endpoint-audit-v1",status="no_endpoint",passed=False,model_calls=0)
    else:
        if arrays["values"].shape!=(2290,) or not all(np.isfinite(v).all() for v in arrays.values()):
            raise ValueError("nonfinite/incomplete endpoint archive")
        result=metric.describe(arrays["values"])
        result.update(schema="tmd-endpoint-audit-v1",status="verified",passed=result["negative"]==0 and result["zero"]==0 and result["min_T_over_sigma"]>1e-8,endpoint_sha256=sha(path),raw_gradient_max=None if "raw_gradient" not in arrays else float(np.abs(arrays["raw_gradient"]).max()),penalized_gradient_max=None if "penalized_gradient" not in arrays else float(np.abs(arrays["penalized_gradient"]).max()),raw_gradient_missing_reason=None if "raw_gradient" in arrays else "model work stopped before raw-gradient endpoint evaluation",model_calls=0)
    result.update(generated_utc=utc(),endpoint_path=path.name if arrays is not None else None,
        atomic_restart_recovery=path.name=='restart.npz')
    write(out/"audit.json",result)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--bundle",required=True); p.add_argument("--out",required=True)
    args=p.parse_args(); result=audit(args.bundle,args.out)
    print(result["status"])
    raise SystemExit(0 if result["passed"] else 2)
