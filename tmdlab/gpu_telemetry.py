"""Persistent UUID-pinned NVML queries, without per-sample subprocesses.

ABI reference: https://docs.nvidia.com/deploy/nvml-api/api/group__nvmlDeviceQueries.html
NVML calls occur on the supervisor's separate sampling thread. Its independent
freshness/deadline watchdog remains active if a driver call ever blocks.
"""
import ctypes as C
import re
import threading
import time

class Memory(C.Structure):
    _fields_=[('total',C.c_ulonglong),('free',C.c_ulonglong),('used',C.c_ulonglong)]

class Utilization(C.Structure):
    _fields_=[('gpu',C.c_uint),('memory',C.c_uint)]

class ProcessInfo(C.Structure):
    _fields_=[('pid',C.c_uint),('usedGpuMemory',C.c_ulonglong),('gpuInstanceId',C.c_uint),('computeInstanceId',C.c_uint)]

def canonical_uuid(value):
    value=str(value).strip()
    value='GPU-'+(value[4:] if value[:4].lower()=='gpu-' else value)
    if not re.fullmatch(r'GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value):
        raise ValueError('invalid physical GPU UUID')
    return value.lower()

class NvmlDevice:
    def __init__(self,uuid,*,library=None,async_optional=False):
        self.uuid=canonical_uuid(uuid)
        self.lib=library if library is not None else C.CDLL('libnvidia-ml.so.1')
        self.check(self.lib.nvmlInit_v2())
        self.handle=C.c_void_p()
        # CUDA properties expose a bare UUID on some supported PyTorch builds;
        # NVML requires the canonical uppercase GPU- prefix for handle lookup.
        nvml_uuid='GPU-'+self.uuid[4:]
        self.check(self.lib.nvmlDeviceGetHandleByUUID(nvml_uuid.encode('ascii'),C.byref(self.handle)))
        observed=self.string('nvmlDeviceGetUUID',self.handle)
        if canonical_uuid(observed)!=self.uuid: raise ValueError('NVML device UUID mismatch')
        self.name=self.string('nvmlDeviceGetName',self.handle)
        self.driver=self.string('nvmlSystemGetDriverVersion')
        self.async_optional=async_optional; self._optional_thread=None; self._optional_snapshot=None

    @staticmethod
    def check(code):
        if code: raise RuntimeError('NVML query failed with code '+str(code))

    def string(self,name,*args):
        value=C.create_string_buffer(128)
        self.check(getattr(self.lib,name)(*args,value,C.c_uint(len(value))))
        return value.value.decode('ascii')

    def optional_sample(self):
        util=Utilization(); power=C.c_uint(); temp=C.c_uint()
        errors={}
        util_code=self.lib.nvmlDeviceGetUtilizationRates(self.handle,C.byref(util))
        power_code=self.lib.nvmlDeviceGetPowerUsage(self.handle,C.byref(power))
        temp_code=self.lib.nvmlDeviceGetTemperature(self.handle,C.c_uint(0),C.byref(temp))
        for name,code in (('utilization',util_code),('power',power_code),('temperature',temp_code)):
            if code: errors[name]=int(code)
        return dict(gpu_utilization_percent=None if util_code else float(util.gpu),
            gpu_memory_utilization_percent=None if util_code else float(util.memory),
            gpu_power_watts=None if power_code else power.value/1000.,
            gpu_temperature_celsius=None if temp_code else float(temp.value),
            optional_gpu_query_errors=errors,optional_sample_monotonic=time.monotonic())

    def optional_cached(self):
        def query():
            try:self._optional_snapshot=self.optional_sample()
            except Exception as exc:
                self._optional_snapshot=dict(optional_gpu_query_errors={'query':str(exc)},optional_sample_monotonic=time.monotonic())
        if self._optional_thread is None or not self._optional_thread.is_alive():
            self._optional_thread=threading.Thread(target=query,daemon=True); self._optional_thread.start()
        saved=self._optional_snapshot
        if saved is not None and time.monotonic()-saved['optional_sample_monotonic']<=2.:return saved
        return dict(optional_gpu_query_errors={'query':'unavailable or older than two seconds'},
            gpu_utilization_percent=None,gpu_memory_utilization_percent=None,gpu_power_watts=None,gpu_temperature_celsius=None)

    def sample(self,pids):
        memory=Memory()
        self.check(self.lib.nvmlDeviceGetMemoryInfo(self.handle,C.byref(memory)))
        # Bound allocation; query changes in process count without an unbounded
        # retry. ProcessInfo is the documented v2/v3 process struct.
        count=C.c_uint(128); processes=(ProcessInfo*128)()
        self.check(self.lib.nvmlDeviceGetComputeRunningProcesses_v3(self.handle,C.byref(count),processes))
        if count.value>128: raise ValueError('GPU process list exceeds bounded sample')
        owned=0
        for process in processes[:count.value]:
            if process.pid in pids:
                if process.usedGpuMemory>=2**63: raise ValueError('GPU process memory unavailable')
                owned+=process.usedGpuMemory
        if not memory.total or memory.used>memory.total: raise ValueError('invalid GPU memory accounting')
        result=dict(gpu_uuid=self.uuid,gpu_name=self.name,gpu_driver=self.driver,
            gpu_owned_gib=owned/2**30,gpu_device_memory_used_gib=memory.used/2**30,
            gpu_device_memory_total_gib=memory.total/2**30,gpu_query_backend='nvml-v3')
        result.update(self.optional_cached() if self.async_optional else self.optional_sample())
        return result
