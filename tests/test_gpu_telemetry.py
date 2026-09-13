import ctypes as C
import pytest
from tmdlab.gpu_telemetry import canonical_uuid,NvmlDevice,ProcessInfo,Memory,Utilization

UUID='GPU-2b0bee61-d667-f75e-14c8-bcc476d83e13'

def test_uuid_requires_full_identity_and_compares_cuda_nvml_forms():
    assert canonical_uuid(UUID)==canonical_uuid(UUID[4:])==canonical_uuid(UUID.lower())
    for value in ('0','6','', 'GPU-fake',UUID+',0'):
        with pytest.raises(ValueError): canonical_uuid(value)

class FakeNvml:
    def nvmlInit_v2(self): return 0
    def nvmlDeviceGetHandleByUUID(self,uuid,target):
        assert uuid==UUID.encode(); return 0
    def nvmlDeviceGetUUID(self,handle,buf,size): buf.value=UUID.encode(); return 0
    def nvmlDeviceGetName(self,handle,buf,size): buf.value=b'RTX A6000'; return 0
    def nvmlSystemGetDriverVersion(self,buf,size): buf.value=b'595.71.05'; return 0
    def nvmlDeviceGetMemoryInfo(self,handle,p):
        m=C.cast(p,C.POINTER(Memory)).contents; m.total=48*2**30; m.used=10*2**30; m.free=38*2**30; return 0
    def nvmlDeviceGetUtilizationRates(self,handle,p):
        m=C.cast(p,C.POINTER(Utilization)).contents; m.gpu=91; m.memory=20; return 0
    def nvmlDeviceGetPowerUsage(self,handle,p): C.cast(p,C.POINTER(C.c_uint)).contents.value=150000; return 0
    def nvmlDeviceGetTemperature(self,handle,sensor,p): C.cast(p,C.POINTER(C.c_uint)).contents.value=55; return 0
    def nvmlDeviceGetComputeRunningProcesses_v3(self,handle,n,processes):
        C.cast(n,C.POINTER(C.c_uint)).contents.value=2
        processes[0]=ProcessInfo(123,3*2**30,0,0)
        processes[1]=ProcessInfo(456,7*2**30,0,0)
        return 0

def test_nvml_attributes_memory_only_to_owned_process_tree():
    result=NvmlDevice(UUID,library=FakeNvml()).sample({123})
    assert result['gpu_owned_gib']==3
    assert result['gpu_device_memory_used_gib']==10
    assert result['gpu_utilization_percent']==91

def test_nvml_errors_fail_closed():
    class Failed(FakeNvml):
        def nvmlDeviceGetMemoryInfo(self,*_):return 15
    with pytest.raises(RuntimeError,match='15'): NvmlDevice(UUID,library=Failed()).sample({123})

def test_optional_query_errors_do_not_discard_mandatory_memory():
    class OptionalFailed(FakeNvml):
        def nvmlDeviceGetUtilizationRates(self,*_):return 3
        def nvmlDeviceGetPowerUsage(self,*_):return 3
        def nvmlDeviceGetTemperature(self,*_):return 3
    result=NvmlDevice(UUID,library=OptionalFailed()).sample({123})
    assert result['gpu_owned_gib']==3
    assert result['gpu_utilization_percent'] is None and result['gpu_power_watts'] is None
    assert result['optional_gpu_query_errors']==dict(utilization=3,power=3,temperature=3)

def test_blocked_optional_query_does_not_block_mandatory_sampling():
    import threading
    import time
    release=threading.Event(); entered=threading.Event()
    class Slow(FakeNvml):
        def nvmlDeviceGetUtilizationRates(self,*args):
            entered.set(); release.wait(timeout=3)
            return super().nvmlDeviceGetUtilizationRates(*args)
    device=NvmlDevice(UUID,library=Slow(),async_optional=True)
    try:
        start=time.monotonic(); result=device.sample({123})
        assert entered.wait(timeout=.5)
        assert time.monotonic()-start<.8 and result['gpu_owned_gib']==3
        assert device.sample({123})['gpu_owned_gib']==3
        assert result['gpu_utilization_percent'] is None
    finally:release.set(); device._optional_thread.join(timeout=1)
