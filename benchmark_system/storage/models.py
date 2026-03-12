from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BenchmarkRun:
    measurement_id: str
    process_name: str
    start_time: datetime
    end_time: datetime | None
    sampling_interval: float


@dataclass
class BenchmarkStep:
    id: int
    measurement_id: str
    function_name: str
    reference: str | None
    start_time: datetime
    end_time: datetime | None


@dataclass
class BenchmarkMetric:
    id: int
    measurement_id: str
    function_name: str
    timestamp: datetime
    cpu: float | None
    ram: float | None
    ram_percent: float | None
    disk_read: float | None
    disk_write: float | None
    io_utilization: float | None
    gpu_utilization: float | None
    gpu_vram_used: float | None
    gpu_vram_total: float | None
    gpu_vram_percent: float | None
    gpu_temperature: float | None
    gpu_power: float | None
    network_rx: float | None
    network_tx: float | None
