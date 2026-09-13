import subprocess
import sys
import time
import pytest
from tmdlab.run import supervise,stop_owned,cgroup_memory_headroom_bytes,parse_gpu_row

BUDGET=dict(rss_gib=48,gpu_gib=20,host_available_gib=8)

def child(seconds=10):
    return subprocess.Popen([sys.executable,"-c",f"import time; time.sleep({seconds})"],start_new_session=True)

def healthy(pid,gpu):
    return dict(monotonic=time.monotonic(),rss_gib=1.,host_available_gib=16.,accepted_updates=0,gpu_owned_gib=2. if gpu else None)

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

def test_v1_cgroup_headroom_uses_process_cgroup_not_node_memory(tmp_path):
    proc=tmp_path/'proc'; pid=4242; mount=tmp_path/'memory'
    path=mount/'slurm'/'job_7'/'step_0'; path.mkdir(parents=True)
    (proc/str(pid)).mkdir(parents=True)
    (proc/str(pid)/'cgroup').write_text('9:memory:/slurm/job_7/step_0\n')
    (proc/'mounts').write_text(f'none {mount} cgroup rw,memory 0 0\n')
    (path/'memory.limit_in_bytes').write_text(str(16*2**30))
    (path/'memory.usage_in_bytes').write_text(str(3*2**30))
    assert cgroup_memory_headroom_bytes(pid,proc_root=proc)==13*2**30

def test_cgroup_headroom_fails_closed_without_finite_limit(tmp_path):
    proc=tmp_path/'proc'; pid=4242; mount=tmp_path/'memory'
    path=mount/'slurm'/'job_7'; path.mkdir(parents=True)
    (proc/str(pid)).mkdir(parents=True)
    (proc/str(pid)/'cgroup').write_text('9:memory:/slurm/job_7\n')
    (proc/'mounts').write_text(f'none {mount} cgroup rw,memory 0 0\n')
    (path/'memory.limit_in_bytes').write_text(str(2**61))
    (path/'memory.usage_in_bytes').write_text('1')
    with pytest.raises(ValueError,match='finite'):
        cgroup_memory_headroom_bytes(pid,proc_root=proc)

def test_allocated_gpu_telemetry_parser_rejects_malformed_rows():
    row='GPU-123, RTX A6000, 595.71.05, 85, 61, 10948, 49140, 192.4, 67'
    parsed=parse_gpu_row(row)
    assert parsed['gpu_uuid']=='GPU-123' and parsed['gpu_utilization_percent']==85
    assert parsed['gpu_device_memory_total_gib']==pytest.approx(49140/1024)
    with pytest.raises(ValueError):
        parse_gpu_row('GPU-123, RTX A6000, 595.71.05, N/A, 61, 1, 2, 3, 4')
