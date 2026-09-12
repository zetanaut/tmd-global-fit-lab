"""Executable bounds; a schema change cannot silently grant extra work."""
import re
from .io import SOURCE_ID, METRIC_ID

def validate_trial(t, *, require_ready=True):
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
    for key,limit in limits.items():
        if type(b[key]) not in (int,float) or not 0 < b[key] <= limit:
            raise ValueError("invalid bounded resource: "+key)
    if b["host_available_gib"] < 8 or b["total_seconds"]-b["segment_seconds"] < 1800:
        raise ValueError("host floor and reserved saved-QA interval required")
    for key in ("full_calls","forwards","accepted_updates","cpu_threads"):
        if type(b[key]) is not int:
            raise ValueError("integer count required")
    phases=t["phases"]
    if t["kind"] == "replay" and phases:
        raise ValueError("replay cannot contain optimizer phases")
    if t["kind"] == "continuation" and (not phases or sum(p["updates"] for p in phases)>b["accepted_updates"]):
        raise ValueError("missing/excess continuation allocation")
    for phase in phases:
        if type(phase["updates"]) is not int or phase["updates"]<1 or phase["mu"] not in (1e-2,1e-3,1e-4,1e-5,1e-6):
            raise ValueError("invalid preregistered phase")
    return t

