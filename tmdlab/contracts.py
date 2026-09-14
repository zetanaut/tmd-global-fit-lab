"""Executable bounds; a schema change cannot silently grant extra work."""
import re
from .io import SOURCE_ID, METRIC_ID, require_finite_numbers

RESUME_TRAJECTORY_LIMITS={
    'p1-resume-v1':dict(accepted_updates=96,forwards=4096,full_calls=512,model_seconds=21600),
    'p1-resume-v2':dict(accepted_updates=192,forwards=8192,full_calls=1024,model_seconds=43200),
}

def validate_trial(t, *, require_ready=True):
    require_finite_numbers(t)
    if t.get("schema") != "tmd-trial-v1" or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,95}",t.get("trial_id","")):
        raise ValueError("invalid trial identity")
    if require_ready and t.get("status") != "ready":
        raise ValueError("trial is not preregistered ready")
    if t["source_identity"] != SOURCE_ID or t["metric_identity"] != METRIC_ID:
        raise ValueError("fixed scientific identity changed")
    if not re.fullmatch(r"[0-9a-f]{64}",t.get("bundle_identity","")):
        raise ValueError("exact bundle identity required")
    if t["kind"] not in ("replay", "continuation") or t["model_family"] != "nested-film-v1":
        raise ValueError("unsupported declared trial/model implementation")
    if t["dtype"] != "float64" or t["rows"] != 2290:
        raise ValueError("all2290 float64 required")
    b=t["budget"]
    limits={"segment_seconds":1800,"total_seconds":7200,"full_calls":240,"forwards":600,"accepted_updates":96,"cache_gib":12,"gpu_gib":20,"rss_gib":48,"cpu_threads":12}
    policy=t.get('execution_policy')
    resumable=policy in RESUME_TRAJECTORY_LIMITS
    if policy not in (None,*RESUME_TRAJECTORY_LIMITS,'paired-feasibility-v1'):
        raise ValueError('unregistered execution policy')
    paired=t.get('execution_policy')=='paired-feasibility-v1'
    if paired:
        if t['kind']!='replay' or t.get('phase')!='W03' or t.get('phases') or t.get('start_checkpoint')!='anchor-w8':
            raise ValueError('paired feasibility is a W03 zero-update anchor check')
        if t['model']!={'width':8,'depth':1} or b['accepted_updates']!=0:
            raise ValueError('paired feasibility has a fixed width8 source and zero optimizer updates')
        if any(b[key] != value for key,value in dict(segment_seconds=1800,total_seconds=3600,forwards=300,full_calls=96,cache_gib=12,cpu_threads=2).items()):
            raise ValueError('paired feasibility resource bound changed')
        start=t.get('paired_start')
        if not isinstance(start,dict) or not re.fullmatch(r'[0-9a-f]{64}',start.get('source_checkpoint_sha256','')):
            raise ValueError('paired feasibility needs pinned source checkpoint')
        if (not isinstance(start.get('seeds'),list) or len(start['seeds'])!=3 or len(set(start['seeds']))!=3
            or any(type(seed) is not int for seed in start['seeds'])
            or type(start.get('radius')) not in (int,float) or not 0<start['radius']<=.1
            or type(start.get('min_diversity_rms')) not in (int,float) or not 0<start['min_diversity_rms']<1):
            raise ValueError('invalid paired start protocol')
    if resumable:
        if t['kind']!='continuation' or t.get('phase')!='P1' or len(t['phases'])!=1 or t['phases'][0]['mu']!=1e-6:
            raise ValueError('resumable policy requires fixed-mu P1')
        limits.update(segment_seconds=13200,total_seconds=13800,full_calls=512,forwards=4096)
    for key,limit in limits.items():
        zero_update = key=='accepted_updates' and t.get('execution_policy')=='paired-feasibility-v1' and b[key]==0
        if type(b[key]) not in (int,float) or not (zero_update or 0 < b[key] <= limit):
            raise ValueError("invalid bounded resource: "+key)
    if b["host_available_gib"] < 8 or b["total_seconds"]-b["segment_seconds"] < (600 if resumable else 1800):
        raise ValueError("host floor and reserved saved-QA interval required")
    for key in ("full_calls","forwards","accepted_updates","cpu_threads"):
        if type(b[key]) is not int:
            raise ValueError("integer count required")
    phases=t["phases"]
    if t["kind"] == "replay" and phases:
        raise ValueError("replay cannot contain optimizer phases")
    if t["kind"] == "continuation" and (not phases or sum(p["updates"] for p in phases)>b["accepted_updates"]):
        raise ValueError("missing/excess continuation allocation")
    if t["kind"] == "continuation":
        if resumable:
            r=t.get('restart_binding',{}); ledger=t.get('trajectory_budget',{})
            trajectory_limits=RESUME_TRAJECTORY_LIMITS[policy]
            if (not re.fullmatch('restart:[0-9a-f]{64}',t.get('start_checkpoint',''))
                or not re.fullmatch('[0-9a-f]{64}',r.get('state_sha256',''))
                or not re.fullmatch('[a-z0-9-]+',r.get('parent_run_id',''))
                or type(r.get('accepted_updates_before')) is not int
                or r['accepted_updates_before']<0 or r.get('optimizer_history_reset') is not False):
                raise ValueError('invalid verified restart binding')
            for key in ('accepted_updates','forwards','full_calls'):
                if type(ledger.get(key)) is not int or not 0<ledger[key]<=trajectory_limits[key]:
                    raise ValueError('invalid cumulative trajectory budget')
            if type(ledger.get('model_seconds')) is not int or not 0<ledger['model_seconds']<=trajectory_limits['model_seconds']:
                raise ValueError('invalid cumulative elapsed budget')
            if (r['accepted_updates_before']+sum(p['updates'] for p in phases)!=ledger['accepted_updates']
                or b.get('endpoint_reserve_seconds',0)<120
                or b['endpoint_reserve_seconds']>=b['segment_seconds']
                or t.get('optimizer',{}).get('line_search') not in ('unit-backtracking','previous-alpha-double')):
                raise ValueError('restart remaining quota/reserve/optimizer mismatch')
        else:
            _validate_fresh_binding(t)
    for phase in phases:
        if type(phase["updates"]) is not int or phase["updates"]<1 or phase["mu"] not in (1e-2,1e-3,1e-4,1e-5,1e-6):
            raise ValueError("invalid preregistered phase")
    start=t.get("start_checkpoint", "")
    if start.startswith("overlay:"):
        if not re.fullmatch(r"overlay:[0-9a-f]{64}", start) or not isinstance(t.get("checkpoint_binding"),dict):
            raise ValueError("exact overlay identity and lineage binding required")
        if t["continuation_binding"]["start_checkpoint_sha256"]!=t["checkpoint_binding"].get("endpoint_sha256"):
            raise ValueError("overlay continuation endpoint binding mismatch")
    return t

def _validate_fresh_binding(t):
        binding=t.get("continuation_binding")
        if not isinstance(binding,dict):
            raise ValueError("continuation needs an exact fresh-allocation binding")
        allocation=binding.get("allocation_id","")
        expected_prefix=t.get("phase","").lower()+"-"
        if (not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,95}",allocation) or
            not allocation.startswith(expected_prefix) or
            binding.get("budget_origin")!="new_allocation" or
            binding.get("optimizer_history_reset") is not True or
            binding.get("prior_phase")!="P0" or
            type(binding.get("accepted_updates_before")) is not int or
            binding["accepted_updates_before"]<1 or
            not re.fullmatch(r"[0-9a-f]{64}",binding.get("start_checkpoint_sha256","") ) or
            type(binding.get("start_q_per_measurement")) not in (int,float) or
            binding["start_q_per_measurement"]<0):
            raise ValueError("invalid continuation lineage/allocation binding")
