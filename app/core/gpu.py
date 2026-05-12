from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from dataclasses import dataclass

import cv2


@dataclass(frozen=True)
class GpuStatus:
    enabled: bool
    required: bool
    configured_device_id: str
    nvidia_visible_devices: str
    cuda_visible_devices: str
    nvidia_smi_available: bool
    nvidia_runtime_visible: bool
    nvidia_device_files: list[str]
    visible_gpu_count: int | None
    opencv_cuda_devices: int
    opencv_cuda_enabled: bool

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _nvidia_smi_count() -> int | None:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    return len([line for line in result.stdout.splitlines() if line.strip().startswith("GPU ")])


def get_gpu_status(enabled: bool, required: bool, configured_device_id: str) -> GpuStatus:
    try:
        opencv_cuda_devices = int(cv2.cuda.getCudaEnabledDeviceCount())
    except Exception:
        opencv_cuda_devices = 0

    nvidia_smi_available = shutil.which("nvidia-smi") is not None
    nvidia_device_files = sorted(
        str(path) for path in Path("/dev").glob("nvidia*") if path.exists()
    )
    nvidia_runtime_visible = bool(nvidia_device_files) or bool(
        os.getenv("NVIDIA_VISIBLE_DEVICES")
    )
    return GpuStatus(
        enabled=enabled,
        required=required,
        configured_device_id=configured_device_id,
        nvidia_visible_devices=os.getenv("NVIDIA_VISIBLE_DEVICES", ""),
        cuda_visible_devices=os.getenv("CUDA_VISIBLE_DEVICES", ""),
        nvidia_smi_available=nvidia_smi_available,
        nvidia_runtime_visible=nvidia_runtime_visible,
        nvidia_device_files=nvidia_device_files,
        visible_gpu_count=_nvidia_smi_count(),
        opencv_cuda_devices=opencv_cuda_devices,
        opencv_cuda_enabled=opencv_cuda_devices > 0,
    )
