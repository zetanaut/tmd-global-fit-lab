"""Saved-only endpoint audit, independent of optimizer success and GPU runtime."""
import argparse
import hashlib
from pathlib import Path
import numpy as np
from .bundle import Bundle
from .metric import Metric
from .io import read,write,sha,utc
from .restart import validate_arrays
from .contracts import RESUME_TRAJECTORY_LIMITS

def endpoint_arrays(out):
    """Choose the atomic restart if KILL left a legacy last-file behind."""
    out=Path(out); path=out/'last.npz'; arrays=None
    if path.is_file():
        with np.load(path,allow_pickle=False) as z:arrays={k:z[k].copy() for k in z.files}
    trial_path=out/'trial.json'
    native=trial_path.is_file() and read(trial_path).get('execution_policy') in RESUME_TRAJECTORY_LIMITS
    restart=out/'restart.npz'
    if native and restart.is_file():
        with np.load(restart,allow_pickle=False) as z:saved={k:z[k].copy() for k in z.files}
        validate_arrays(saved,saved['theta'].size)
        if arrays is None or any(not np.array_equal(arrays.get(k),saved[k]) for k in ('theta','values','penalized_gradient')):
            return restart,{k:saved[k] for k in ('theta','values','penalized_gradient')}
    return path,arrays

def audit(bundle_dir,out):
    out=Path(out); bundle=Bundle(bundle_dir); metric=Metric(bundle)
    trial_path=out/'trial.json'
    if trial_path.is_file() and read(trial_path).get('execution_policy')=='paired-feasibility-v1':
        return paired_audit(metric,out)
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

def paired_audit(metric,out):
    """Saved-only audit of every W03 endpoint, with no model dispatch."""
    report_path=out/'worker'/'paired-feasibility.json'
    if not report_path.is_file():
        result=dict(schema='tmd-paired-feasibility-audit-v1',status='no_paired_report',passed=False,model_calls=0)
        write(out/'audit.json',result); return result
    report=read(report_path); trial=read(out/'trial.json'); failures=[]; endpoints=0
    seeds=trial['paired_start']['seeds']; expected_seeds={str(seed) for seed in seeds}
    if (report.get('status')!='passed' or report.get('rows')!=2290 or report.get('dtype')!='float64'
        or report.get('source_identity')!=trial['source_identity'] or report.get('metric_identity')!=trial['metric_identity']
        or report.get('bundle_identity')!=trial['bundle_identity'] or report.get('source_checkpoint')!=trial['start_checkpoint']
        or report.get('source_checkpoint_sha256')!=trial['paired_start']['source_checkpoint_sha256']
        or report.get('seeds')!=seeds or set(report.get('candidates',{}))!=expected_seeds):
        failures.append('invalid paired report')
    counters=report.get('counters',{})
    if (counters.get('accepted_updates')!=0 or not 63<=counters.get('forwards',0)<=trial['budget']['forwards']
        or not 18<=counters.get('full_calls',0)<=trial['budget']['full_calls'] or counters.get('call_in_flight')):
        failures.append('invalid paired counters')
    narrow_values={}; parameter_counts={8:1570,16:2882,24:4706}
    worker_root=(out/'worker').resolve()
    for seed, candidate in report.get('candidates',{}).items():
        base=None; base_value=None
        for width in ('8','16','24'):
            cell=candidate.get('widths',{}).get(width,{})
            relative=Path(cell.get('endpoint_path',''))
            path=(worker_root/relative).resolve()
            if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(worker_root) or not path.is_file() or sha(path)!=cell.get('endpoint_sha256'):
                failures.append(f'{seed}/w{width} endpoint identity'); continue
            with np.load(path,allow_pickle=False) as z: arrays={key:z[key].copy() for key in z.files}
            expected_count=parameter_counts[int(width)]
            if (set(arrays)!={'theta','values','raw_gradient','penalized_gradient'} or arrays['values'].shape!=(2290,)
                or any(value.dtype!=np.float64 or not np.isfinite(value).all() for value in arrays.values())
                or any(arrays[key].shape!=(expected_count,) for key in ('theta','raw_gradient','penalized_gradient'))):
                failures.append(f'{seed}/w{width} endpoint arrays'); continue
            point=metric.score(arrays['values'],1e-6)
            if point is None or point['min_T_over_sigma']<=1e-8:
                failures.append(f'{seed}/w{width} feasibility'); continue
            directional=cell.get('directional',[])
            if (len(directional)!=2 or not all(item.get('passed') and any(attempt.get('feasible') and isinstance(attempt.get('error'),float)
                and np.isfinite(attempt['error']) and attempt['error']<2e-6 for attempt in item.get('attempts',[])) for item in directional)):
                failures.append(f'{seed}/w{width} directional')
            if width=='8':
                receipt=candidate.get('receipt',{})
                theta_hash=hashlib.sha256(np.ascontiguousarray(arrays['theta'],dtype=np.float64).tobytes()).hexdigest()
                if receipt.get('seed')!=int(seed) or theta_hash!=receipt.get('candidate_parameter_sha256'):
                    failures.append(f'{seed}/w8 candidate receipt')
                base=point; base_value=arrays['values']
            else:
                pair=cell.get('paired_to_width8',{})
                delta=np.abs(arrays['values']-base_value)/metric.sigma if base_value is not None else np.array([np.inf])
                q_error=abs(point['q_per_measurement']-base['q_per_measurement']) if base is not None else np.inf
                if (base is None or pair.get('prediction_error_fixed_sigma')!=float(delta.max())
                    or pair.get('q_error')!=q_error or float(delta.max())>1e-7 or q_error>1e-8):
                    failures.append(f'{seed}/w{width} transport')
            endpoints+=1
        if base_value is not None:
            narrow_values[int(seed)]=base_value
    diversity=[]
    for i,left in enumerate(seeds):
        for right in seeds[i+1:]:
            if left not in narrow_values or right not in narrow_values:
                failures.append('missing narrow endpoint for diversity'); continue
            delta=(narrow_values[left]-narrow_values[right])/metric.sigma
            diversity.append(float(np.sqrt(np.mean(delta**2))))
    if len(diversity)!=3 or any(value<trial['paired_start']['min_diversity_rms'] for value in diversity):
        failures.append('candidate diversity')
    result=dict(schema='tmd-paired-feasibility-audit-v1',status='verified' if not failures and endpoints==9 else 'failed',
        passed=not failures and endpoints==9, endpoints_verified=endpoints, failures=failures, model_calls=0,
        report_sha256=sha(report_path), generated_utc=utc())
    write(out/'audit.json',result)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--bundle",required=True); p.add_argument("--out",required=True)
    args=p.parse_args(); result=audit(args.bundle,args.out)
    print(result["status"])
    raise SystemExit(0 if result["passed"] else 2)
