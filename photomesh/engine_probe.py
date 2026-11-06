"""Probe the CUDA driver in an expendable child, never in the GUI process."""
import ctypes
import json
import os



def probe():
    if os.environ.get("PHOTOMESH_FORCE_NO_GPU"):
        return {"devices": [], "reason": "GPU disabled by environment"}
    try:
        cuda = ctypes.WinDLL("nvcuda.dll") if os.name == "nt" else ctypes.CDLL("libcuda.so.1")
        if cuda.cuInit(0) != 0:
            return {"devices": [], "reason": "CUDA driver initialization failed"}
        driver = ctypes.c_int()
        count = ctypes.c_int()
        if cuda.cuDriverGetVersion(ctypes.byref(driver)) or cuda.cuDeviceGetCount(ctypes.byref(count)):
            return {"devices": [], "reason": "CUDA device enumeration failed"}
        devices = []
        for index in range(count.value):
            device = ctypes.c_int()
            if cuda.cuDeviceGet(ctypes.byref(device), index):
                continue
            name = ctypes.create_string_buffer(256)
            major, minor = ctypes.c_int(), ctypes.c_int()
            total = ctypes.c_size_t()
            if cuda.cuDeviceGetName(name, len(name), device):
                continue
            if cuda.cuDeviceComputeCapability(ctypes.byref(major), ctypes.byref(minor), device):
                continue
            memory = (getattr(cuda, "cuDeviceTotalMem_v2", None) or getattr(cuda, "cuDeviceTotalMem"))
            if memory(ctypes.byref(total), device):
                continue
            devices.append({"index": index, "name": name.value.decode("utf-8", "replace"),
                            "cc": major.value * 10 + minor.value, "memory": total.value})
        return {"devices": devices, "driver": driver.value}
    except (OSError, AttributeError) as error:
        return {"devices": [], "reason": str(error)}


if __name__ == "__main__":
    print(json.dumps(probe()))
