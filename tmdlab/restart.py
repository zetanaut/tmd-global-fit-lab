"""Verified L-BFGS restart state; saved arrays only, no model evaluation."""
from pathlib import Path
import re
import math
import numpy as np
from .io import read, write, sha, digest, within

COUNTERS = ('forwards', 'full_calls', 'accepted_updates', 'infeasible_trials', 'line_search_rejections')
ALGORITHM = 'lbfgs15-armijo32-sy1e-12-v1'

def update_history(history, old_theta, old_gradient, theta, gradient):
    s = theta-old_theta; y = gradient-old_gradient; sy = float(s@y)
    if sy > 1e-12 and np.isfinite(sy):
        history.append((s, y, 1/sy))
    return history[-15:]

def pack_state(point, history, states, counts, *, mu, last_alpha=1.):
    n = point['theta'].size
    return dict(theta=point['theta'], values=point['values'],
        penalized_gradient=point['gradient'], mu=np.array(mu),
        last_alpha=np.array(last_alpha),
        history_s=np.stack([s for s, _, _ in history]) if history else np.empty((0,n)),
        history_y=np.stack([y for _, y, _ in history]) if history else np.empty((0,n)),
        history_rho=np.array([rho for _, _, rho in history]),
        state_values=np.stack([s['values'] for s in states]),
        state_q=np.array([s['q_per_measurement'] for s in states]),
        state_gradient_max=np.array([s['gradient_max'] for s in states]),
        state_mu=np.array([s['mu'] for s in states]),
        counters=np.array([counts[k] for k in COUNTERS], dtype=np.int64))

def validate_arrays(a, parameters):
    n = parameters; h = len(a['history_rho']); s = len(a['state_q'])
    shapes = dict(theta=(n,), values=(2290,), penalized_gradient=(n,), mu=(), last_alpha=(),
        history_s=(h,n), history_y=(h,n), history_rho=(h,), state_values=(s,2290),
        state_q=(s,), state_gradient_max=(s,), state_mu=(s,), counters=(len(COUNTERS),))
    if set(a) != set(shapes) or not 0 <= h <= 15 or not 1 <= s <= 21:
        raise ValueError('restart inventory/history/window mismatch')
    for key, shape in shapes.items():
        dtype = np.int64 if key == 'counters' else np.float64
        if a[key].shape != shape or a[key].dtype != dtype or not np.isfinite(a[key]).all():
            raise ValueError('restart array shape/dtype/finite mismatch: '+key)
    if (a['counters'] < 0).any() or (a['history_rho'] <= 0).any() or not 0 < a['last_alpha'] <= 1:
        raise ValueError('invalid restart counts/history/alpha')
    if not np.array_equal(a['values'], a['state_values'][-1]) or not (a['state_mu'] == a['mu']).all():
        raise ValueError('restart endpoint/window phase mismatch')
    for x,y,rho in zip(a['history_s'],a['history_y'],a['history_rho']):
        sy = float(x@y)
        if sy <= 1e-12 or not np.isclose(rho,1/sy,rtol=1e-13,atol=0):
            raise ValueError('invalid restart curvature pair')
    if a['state_gradient_max'][-1] != np.max(np.abs(a['penalized_gradient'])):
        raise ValueError('restart endpoint gradient mismatch')
    return a

def unpack_state(a, metric):
    point = metric.score(a['values'],float(a['mu']))
    if point is None: raise ValueError('infeasible saved restart')
    if abs(point['q_per_measurement']-a['state_q'][-1]) > 1e-10:
        raise ValueError('restart saved metric mismatch')
    point.update(theta=a['theta'].copy(), gradient=a['penalized_gradient'].copy(),
        mu=float(a['mu']), gradient_max=float(a['state_gradient_max'][-1]))
    history = [(s.copy(),y.copy(),float(r)) for s,y,r in zip(a['history_s'],a['history_y'],a['history_rho'])]
    states = [dict(values=v.copy(),q_per_measurement=float(q),gradient_max=float(g),mu=float(mu))
        for v,q,g,mu in zip(a['state_values'],a['state_q'],a['state_gradient_max'],a['state_mu'])]
    return point, history, states, dict(zip(COUNTERS,map(int,a['counters'])))

def load_restart(root, identity, trial, bundle):
    if not re.fullmatch('[0-9a-f]{64}',identity): raise ValueError('invalid restart identity')
    m = read(within(root,'restarts/'+identity+'.json'))
    if m.get('identity') != identity or digest({k:v for k,v in m.items() if k!='identity'}) != identity:
        raise ValueError('restart manifest identity mismatch')
    if m.get('schema') != 'tmd-optimizer-restart-v1' or m['algorithm'] != ALGORITHM:
        raise ValueError('unsupported restart algorithm')
    for key in ('bundle_identity','source_identity','metric_identity','model'):
        if m[key] != trial[key]: raise ValueError('restart scientific/model mismatch: '+key)
    if bundle.index['identity'] != m['bundle_identity']: raise ValueError('restart bundle mismatch')
    parent=m['parent_record']; parent_path=within(root,parent['path'])
    if sha(parent_path)!=parent['sha256']:
        raise ValueError('restart parent result hash mismatch')
    from .results import validate_record
    parent_result=validate_record(read(parent_path))
    if parent_result['run_id']!=m['parent_run_id'] or parent_result['artifact']!=m['artifact']:
        raise ValueError('restart parent result/artifact mismatch')
    obj = m['object']; path = within(root,obj['path'])
    if obj['path'] != 'checkpoint-objects/'+obj['sha256']+'.npz' or sha(path)!=obj['sha256'] or path.stat().st_size!=obj['bytes']:
        raise ValueError('restart object hash/size mismatch')
    with np.load(path,allow_pickle=False) as z: a = {k:z[k].copy() for k in z.files}
    validate_arrays(a,m['parameters'])
    if dict(zip(COUNTERS,map(int,a['counters'])))!=m['counters']:
        raise ValueError('restart manifest/counter mismatch')
    binding = trial['restart_binding']
    if (binding['parent_run_id'] != m['parent_run_id'] or binding['state_sha256'] != obj['sha256']
        or binding['accepted_updates_before'] != int(a['counters'][2])
        or float(a['mu']) != trial['phases'][0]['mu']):
        raise ValueError('restart trial lineage/mu mismatch')
    return m,a

def elapsed_before(root, manifest, seen=None):
    """Reconcile elapsed model windows from immutable ancestor result receipts.

    Initial imported manifests predate the elapsed field. Their parent result
    is still authoritative; absence is never interpreted as zero prior work.
    """
    seen=set() if seen is None else seen
    identity=manifest['identity']
    if identity in seen:raise ValueError('restart lineage cycle')
    seen.add(identity)
    if digest({k:v for k,v in manifest.items() if k!='identity'})!=identity:
        raise ValueError('restart elapsed manifest identity mismatch')
    parent=manifest['parent_record']; path=within(root,parent['path'])
    if sha(path)!=parent['sha256']:raise ValueError('restart elapsed parent hash mismatch')
    record=read(path)
    if record['run_id']!=manifest['parent_run_id']:raise ValueError('restart elapsed parent run mismatch')
    elapsed=record['supervisor'].get('elapsed_seconds')
    if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:
        raise ValueError('missing finite parent model elapsed evidence')
    start=record['start_checkpoint']
    if start.startswith('restart:'):
        prior=read(within(root,'restarts/'+start[8:]+'.json'))
        if prior['identity']!=start[8:]:raise ValueError('restart elapsed ancestor identity mismatch')
        elapsed+=elapsed_before(root,prior,seen)
    if 'model_seconds_before' in manifest and not math.isclose(manifest['model_seconds_before'],elapsed,rel_tol=0,abs_tol=1e-6):
        raise ValueError('restart elapsed ledger mismatch')
    return elapsed

def segment_allowance(trial, prior_seconds):
    remaining=trial['trajectory_budget']['model_seconds']-prior_seconds
    allowed=min(trial['budget']['segment_seconds'],remaining)
    if allowed<=trial['budget']['endpoint_reserve_seconds']:
        raise ValueError('trajectory elapsed budget exhausted; preregister a decision before further work')
    return allowed

def reconstruct_v1(run, record):
    """Recover history from EVERY accepted theta AND gradient, with source proof.

    This deliberately supports only archived, single-phase legacy P1 runs.
    It rejects missing transitions and counts beyond the last saved endpoint.
    """
    run=Path(run); trial=read(run/'trial.json'); launch=read(run/'launch.json')
    if launch['run_id']!=record['run_id'] or trial['kind']!='continuation' or len(trial['phases'])!=1:
        raise ValueError('only verified single-phase continuation imports supported')
    for name,item in record['files'].items():
        path=within(run,name)
        if sha(path)!=item['sha256'] or path.stat().st_size!=item['bytes']:
            raise ValueError('published run file mismatch: '+name)
    summary=read(run/'worker-summary.json') if (run/'worker-summary.json').is_file() else {}
    counts=summary.get('counters') or read(run/'counters.json')
    counts={k:counts[k] for k in COUNTERS}; n=counts['accepted_updates']
    if len(list(run.glob('accepted-*.json')))!=n or len(list(run.glob('checkpoint-*.npz')))!=n:
        raise ValueError('incomplete accepted transition chain')
    with np.load(run/'initial.npz',allow_pickle=False) as z:
        old_theta=z['theta'].copy(); old_gradient=z['penalized_gradient'].copy(); initial=z['values'].copy()
    mu=trial['phases'][0]['mu']; history=[]; states=[]; last_alpha=1.
    # Initial q is pinned by the starting continuation binding.
    states.append(dict(values=initial,q_per_measurement=trial['continuation_binding']['start_q_per_measurement'],
        gradient_max=float(np.max(np.abs(old_gradient))),mu=mu))
    for i in range(1,n+1):
        step=read(run/f'accepted-{i:03d}.json')
        if step['accepted_updates']!=i or step['mu']!=mu: raise ValueError('transition index/phase mismatch')
        with np.load(run/f'checkpoint-{i:03d}.npz',allow_pickle=False) as z:
            theta=z['theta'].copy(); gradient=z['penalized_gradient'].copy(); values=z['values'].copy()
        # Imported locally to avoid torch dependency for other saved-only tools.
        from .lbfgs import two_loop
        direction=-two_loop(old_gradient,history)
        if not np.isfinite(direction).all() or float(old_gradient@direction)>=0:
            direction=-old_gradient
        if np.max(np.abs(theta-(old_theta+step['alpha']*direction))) > 1e-12:
            raise ValueError('accepted transition does not replay within float64 tolerance')
        history=update_history(history,old_theta,old_gradient,theta,gradient)
        old_theta,old_gradient=theta,gradient; last_alpha=step['alpha']
        states.append(dict(values=values,q_per_measurement=step['q_per_measurement'],gradient_max=float(np.max(np.abs(gradient))),mu=mu))
        states=states[-21:]
    with np.load(run/'last.npz',allow_pickle=False) as z:
        if not np.array_equal(z['theta'],old_theta) or not np.array_equal(z['values'],states[-1]['values']):
            raise ValueError('last endpoint differs from final accepted state')
    point=dict(theta=old_theta,values=states[-1]['values'],gradient=old_gradient)
    a=pack_state(point,history,states,counts,mu=mu,last_alpha=last_alpha)
    return validate_arrays(a,old_theta.size)

def recover_native(run, record):
    """Restore atomic optimizer state and reconcile every charged dispatch.

    A hard kill can leave the checkpoint's call ledger older than counters.json.
    Preserve its optimizer state but take the greatest observed charge for each
    counter. An accepted step beyond the atomic state requires investigation.
    """
    run=Path(run)
    for name,item in record['files'].items():
        path=within(run,name)
        if sha(path)!=item['sha256'] or path.stat().st_size!=item['bytes']:
            raise ValueError('published run file mismatch: '+name)
    with np.load(run/'restart.npz',allow_pickle=False) as z:a={k:z[k].copy() for k in z.files}
    validate_arrays(a,a['theta'].size)
    audit=record.get('audit') or {}
    if not audit.get('passed'):raise ValueError('native restart requires saved endpoint audit')
    endpoint=within(run,audit.get('endpoint_path') or 'last.npz')
    if sha(endpoint)!=audit['endpoint_sha256']:raise ValueError('native audited endpoint hash mismatch')
    with np.load(endpoint,allow_pickle=False) as z:
        if any(not np.array_equal(z[k],a[k]) for k in ('theta','values','penalized_gradient')):
            raise ValueError('native restart differs from audited endpoint')
    counts=dict(zip(COUNTERS,map(int,a['counters'])))
    if 'counters.json' not in record['files'] or not (run/'counters.json').is_file():
        raise ValueError('native restart requires hash-bound terminal dispatch ledger')
    for name in ('counters.json','worker-summary.json'):
        if not (run/name).is_file():continue
        charged=read(run/name).get('trajectory_counters')
        if not charged:raise ValueError('native restart needs cumulative dispatch ledger')
        if charged['accepted_updates']>counts['accepted_updates']:
            raise ValueError('accepted work beyond atomic restart state')
        for key in COUNTERS:
            if type(charged[key]) is not int or charged[key]<0:raise ValueError('invalid charged work')
            counts[key]=max(counts[key],charged[key])
    a['counters']=np.array([counts[k] for k in COUNTERS],dtype=np.int64)
    return a
