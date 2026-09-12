"""One bounded trial, launched only by the external supervisor."""
import argparse
from dataclasses import asdict
import json
import importlib.metadata
import os
from pathlib import Path
import signal
import time
import traceback
import numpy as np
import torch
from .io import read,write,sha,digest,utc
from .bundle import Bundle
from .metric import Metric
from .models import build,Config,schema
from .engine import Engine
from .contracts import validate_trial

class Stop(RuntimeError):
    pass

def plateau(states,sigma):
    if len(states)<21:
        return dict(eligible=False,passed=False,reason="fewer_than_21_states")
    windows=[]
    for w in (states[-21:-10],states[-11:]):
        span=np.ptp(np.array([s["values"] for s in w])/sigma,axis=0)
        r=dict(q_range=float(np.ptp([s["q_per_measurement"] for s in w])),prediction_span_rms=float(np.sqrt(np.mean(span**2))),prediction_span_max=float(span.max()),gradient_max=float(w[-1]["gradient_max"]),same_mu=len({s["mu"] for s in w})==1)
        r["passed"]=r["same_mu"] and r["q_range"]<=1e-4 and r["prediction_span_rms"]<=1e-3 and r["prediction_span_max"]<=1e-2 and r["gradient_max"]<=1e-5
        windows.append(r)
    return dict(eligible=True,passed=all(w["passed"] for w in windows) and states[-21]["mu"]==states[-1]["mu"],windows=windows)

def two_loop(gradient,history):
    q=gradient.copy(); alphas=[]
    for s,y,rho in reversed(history):
        alpha=rho*float(s@q); alphas.append(alpha); q-=alpha*y
    gamma=1.
    if history:
        s,y,_=history[-1]; gamma=max(min(float(s@y)/max(float(y@y),1e-300),1e6),1e-12)
    r=gamma*q
    for (s,y,rho),alpha in zip(history,reversed(alphas)):
        r+=s*(alpha-rho*float(y@r))
    return r

def save_npz(path,**arrays):
    path=Path(path)
    temp=path.with_suffix(".pending.npz")
    np.savez_compressed(temp,**arrays)
    with temp.open("rb") as f: os.fsync(f.fileno())
    os.replace(temp,path)

def run(args):
    trial=validate_trial(read(args.trial)); budget=trial["budget"]
    launch=read(args.out/"launch.json")
    if launch["trial_sha256"]!=sha(args.trial): raise ValueError("trial changed after acceptance")
    deadline=float(launch["model_deadline_monotonic"])
    torch.set_num_threads(budget["cpu_threads"] if args.device=="cpu" else 1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    write(args.out/"environment.json",dict(packages={k:importlib.metadata.version(k) for k in ("numpy","scipy","torch","psutil")},torch_cuda_build=torch.version.cuda,gpu_name=torch.cuda.get_device_name(0) if args.device.startswith("cuda") else None,dtype="float64",deterministic_algorithms=True,TF32=False,torch_threads=torch.get_num_threads()))
    def term(*_): raise Stop("supervisor/model deadline or resource stop")
    signal.signal(signal.SIGTERM,term)
    engine=None; point=None; states=[]; history=[]
    counts=dict(forwards=0,full_calls=0,accepted_updates=0,infeasible_trials=0,line_search_rejections=0)
    status="failed"; reason=None; phase_records=[]; preflight={}
    def guard():
        if time.monotonic()>=deadline: raise Stop("segment_time_cap")
    def call(theta,cot=None):
        guard()
        if counts["forwards"]>=budget["forwards"] or cot is not None and counts["full_calls"]>=budget["full_calls"]: raise Stop("call_budget")
        counts["forwards"]+=1
        if cot is not None: counts["full_calls"]+=1
        write(args.out/"counters.json",dict(counts,time_utc=utc(),call_in_flight=True))
        result=engine.evaluate(theta,cot,deadline=deadline)
        write(args.out/"counters.json",dict(counts,time_utc=utc(),call_in_flight=False))
        guard()
        return result
    def full(theta,mu):
        values,_=call(theta)
        p=metric.score(values,mu)
        if p is None:
            counts["infeasible_trials"]+=1
            return None
        replay,g=call(theta,p["cotangent"])
        if not np.array_equal(replay,values): raise ValueError("same-device forward/VJP mismatch")
        return dict(p,theta=theta.copy(),gradient=g,mu=mu,gradient_max=float(np.max(np.abs(g))))
    try:
        guard(); bundle=Bundle(args.bundle)
        if bundle.index["identity"]!=trial["bundle_identity"]: raise ValueError("wrong pinned input bundle")
        metric=Metric(bundle)
        entry,saved=bundle.checkpoint(trial["start_checkpoint"])
        cfg=Config(**trial["model"])
        if asdict(cfg)!=asdict(Config(**entry["model"])): raise ValueError("checkpoint/model mismatch; a new initialization must be registered first")
        model=build(cfg,trial["seed"])
        if schema(model)!=entry["parameter_schema"]: raise ValueError("checkpoint parameter order/schema changed")
        theta=saved["theta"].copy()
        guard(); engine=Engine(model,bundle,args.device,cache_gib=budget["cache_gib"],deadline=deadline)
        write(args.out/"preparation.json",dict(cache_bytes=engine.cache_bytes,groups=len(engine.groups),elapsed_seconds=time.monotonic()-launch["t0_monotonic"]))
        mu=trial["phases"][0]["mu"] if trial["phases"] else 1e-6
        point=full(theta,mu)
        if point is None: raise ValueError("start is not strictly feasible")
        pred_error=float(np.max(np.abs(point["values"]-saved["values"])/metric.sigma))
        q_error=abs(point["q_per_measurement"]-entry["q_per_measurement"])
        preflight=dict(prediction_error_fixed_sigma=pred_error,q_error=q_error)
        if pred_error>1e-7 or q_error>1e-8: raise ValueError("portable checkpoint replay failed")
        _,raw=call(theta,point["raw_cotangent"])
        if "raw_gradient" in saved:
            grad_error=float(np.max(np.abs(raw-saved["raw_gradient"])))
            preflight["raw_gradient_error"]=grad_error
            if grad_error>1e-7: raise ValueError("portable raw-gradient replay failed")
        directions=[]; rng=np.random.default_rng(trial["seed"])
        for i in range(2):
            d=rng.normal(size=theta.size); d/=np.linalg.norm(d)
            analytic=float(point["gradient"]@d); attempts=[]; passed=False
            h=1e-5
            while h>=1e-10:
                plus,_=call(theta+h*d); minus,_=call(theta-h*d)
                p,m=metric.score(plus,mu),metric.score(minus,mu)
                error=None if p is None or m is None else abs((p["objective"]-m["objective"])/(2*h)-analytic)
                attempts.append(dict(h=h,error=error,feasible=p is not None and m is not None))
                if error is not None and error<2e-6: passed=True; break
                h*=.5
            directions.append(dict(direction=i,passed=passed,attempts=attempts))
            if not passed: raise ValueError("active-mu directional check failed")
        preflight.update(directional=directions,passed=True)
        write(args.out/"preflight.json",preflight)
        save_npz(args.out/"initial.npz",theta=theta,values=point["values"],raw_gradient=raw,penalized_gradient=point["gradient"])
        save_npz(args.out/"last.npz",theta=theta,values=point["values"],raw_gradient=raw,penalized_gradient=point["gradient"])
        for phase_index,phase in enumerate(trial["phases"]):
            if phase_index:
                point=full(point["theta"],phase["mu"])
                if point is None: raise ValueError("phase entry infeasible")
            states=[dict(point)]; history=[]; phase_steps=0
            for step in range(phase["updates"]):
                guard()
                direction=-two_loop(point["gradient"],history)
                gdot=float(point["gradient"]@direction)
                if not np.isfinite(direction).all() or gdot>=0:
                    direction=-point["gradient"]; gdot=float(point["gradient"]@direction)
                if gdot>=0: raise Stop("non_descent_direction")
                accepted=None; alpha=1.
                for attempt in range(32):
                    candidate=full(point["theta"]+alpha*direction,phase["mu"])
                    if candidate is not None and candidate["objective"]<=point["objective"]+1e-4*alpha*gdot:
                        accepted=candidate; break
                    counts["line_search_rejections"]+=1; alpha*=.5
                if accepted is None: raise Stop("line_search_exhausted_32_trials")
                s=accepted["theta"]-point["theta"]; y=accepted["gradient"]-point["gradient"]; sy=float(s@y)
                if sy>1e-12 and np.isfinite(sy): history.append((s,y,1/sy)); history=history[-15:]
                point=accepted; counts["accepted_updates"]+=1; phase_steps+=1
                states.append(dict(point)); states=states[-21:]
                step=counts["accepted_updates"]
                save_npz(args.out/f"checkpoint-{step:03d}.npz",theta=point["theta"],values=point["values"],penalized_gradient=point["gradient"])
                save_npz(args.out/"last.npz",theta=point["theta"],values=point["values"],penalized_gradient=point["gradient"])
                write(args.out/f"accepted-{step:03d}.json",dict(counts,mu=phase["mu"],q_per_measurement=point["q_per_measurement"],objective=point["objective"],alpha=alpha,plateau=plateau(states,metric.sigma)))
            phase_records.append(dict(mu=phase["mu"],accepted=phase_steps,requested=phase["updates"],plateau=plateau(states,metric.sigma)))
        _,raw=call(point["theta"],point["raw_cotangent"])
        save_npz(args.out/"last.npz",theta=point["theta"],values=point["values"],raw_gradient=raw,penalized_gradient=point["gradient"])
        status="completed"; reason="replay_passed" if trial["kind"]=="replay" else "phase_schedule_complete"
    except Stop as exc:
        status="partial"; reason=str(exc)
    except Exception as exc:
        reason=type(exc).__name__+": "+str(exc)
        write(args.out/"failure.json",dict(error=reason,traceback=traceback.format_exc()))
    finally:
        if engine is not None: engine.close()
        write(args.out/"worker-summary.json",dict(schema="tmd-worker-v1",status=status,stop_reason=reason,counters=counts,phases=phase_records,preflight=preflight,optimizer_history_reset=True,uninterrupted_trajectory=False,plateau=plateau(states,metric.sigma) if "metric" in locals() else None,end_utc=utc()))
    return 0 if status=="completed" else 2

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trial",type=Path,required=True); p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True); p.add_argument("--device",required=True)
    raise SystemExit(run(p.parse_args()))
