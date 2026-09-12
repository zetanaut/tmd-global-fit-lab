import subprocess
import sys
import time
import pytest
from tmdlab.run import supervise,stop_owned

BUDGET=dict(rss_gib=48,gpu_gib=20,host_available_gib=8)

def child(seconds=10):
    return subprocess.Popen([sys.executable,"-c",f"import time; time.sleep({seconds})"],start_new_session=True)

def healthy(pid,gpu):
    return dict(monotonic=time.monotonic(),rss_gib=1.,host_available_gib=16.,gpu_owned_gib=2. if gpu else None)

def test_deadline_does_not_wait_for_slow_sampler(tmp_path):
    p=child();started=time.monotonic()
    def slow(pid,gpu):time.sleep(2.5);return healthy(pid,gpu)
    try:result=supervise(p,deadline=started+.15,budget=BUDGET,gpu=False,out=tmp_path,sampler=slow)
    finally:stop_owned(p)
    assert result["stop_reason"]=="model_deadline"
    # Thread shutdown may consume1s; process stop is already recorded/reaped.
    assert time.monotonic()-started<2.
    assert p.poll() is not None

def test_stale_telemetry_fails_closed(tmp_path):
    p=child()
    def stale(pid,gpu):return dict(healthy(pid,gpu),monotonic=time.monotonic()-2)
    try:r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=stale)
    finally:stop_owned(p)
    assert r["stop_reason"]=="telemetry_stale_over_1s"

def test_malformed_telemetry_fails_closed(tmp_path):
    p=child()
    def malformed(pid,gpu):return dict(healthy(pid,gpu),rss_gib=float("nan"))
    try:r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=malformed)
    finally:stop_owned(p)
    assert r["stop_reason"].startswith("telemetry_failure")

def test_limit_stops_only_owned_process(tmp_path):
    p=child();unrelated=child()
    def high(pid,gpu):return dict(healthy(pid,gpu),rss_gib=49.)
    try:
        r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=high)
        assert r["stop_reason"]=="resource_limit"
        assert unrelated.poll() is None
    finally:stop_owned(p);stop_owned(unrelated)

def test_real_sample_peaks_persist(tmp_path):
    p=child(.6);count=0
    def rising(pid,gpu):
        nonlocal count
        count+=1
        return dict(healthy(pid,gpu),rss_gib=float(count))
    try:r=supervise(p,deadline=time.monotonic()+3,budget=BUDGET,gpu=False,out=tmp_path,sampler=rising)
    finally:stop_owned(p)
    assert r["stop_reason"] is None
    assert r["peaks"]["rss_gib"]>=2
    assert r["peaks"]["samples"]>=2
    assert (tmp_path/"resources.ndjson").read_text().strip()
