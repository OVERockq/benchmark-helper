from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class GlancesClient:
    def __init__(self, base_url: str = "http://localhost:61208/api/3", timeout: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, endpoint: str) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        req = Request(url, method="GET")
        with urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def sample(self) -> dict[str, float | None]:
        metrics: dict[str, float | None] = {
            "cpu": None,
            "ram": None,
            "ram_percent": None,
            "disk_read": None,
            "disk_write": None,
            "io_utilization": None,
            "gpu_utilization": None,
            "gpu_vram_used": None,
            "gpu_vram_total": None,
            "gpu_vram_percent": None,
            "gpu_temperature": None,
            "gpu_power": None,
            "network_rx": None,
            "network_tx": None,
        }

        try:
            cpu = self._get("cpu")
            metrics["cpu"] = float(cpu.get("total", 0.0))
        except (URLError, ValueError, KeyError, TypeError):
            pass

        try:
            mem = self._get("mem")
            metrics["ram"] = float(mem.get("used", 0.0))
            metrics["ram_percent"] = float(mem.get("percent", 0.0))
        except (URLError, ValueError, KeyError, TypeError):
            pass

        try:
            disks = self._get("diskio")
            if isinstance(disks, list) and disks:
                metrics["disk_read"] = float(sum(d.get("read_bytes", 0.0) for d in disks))
                metrics["disk_write"] = float(sum(d.get("write_bytes", 0.0) for d in disks))
                utils = [d.get("time_since_update") for d in disks if isinstance(d.get("time_since_update"), (int, float))]
                metrics["io_utilization"] = float(sum(utils) / len(utils)) if utils else None
        except (URLError, ValueError, KeyError, TypeError, ZeroDivisionError):
            pass

        try:
            net = self._get("network")
            if isinstance(net, list) and net:
                metrics["network_rx"] = float(sum(n.get("rx", 0.0) for n in net))
                metrics["network_tx"] = float(sum(n.get("tx", 0.0) for n in net))
        except (URLError, ValueError, KeyError, TypeError):
            pass

        try:
            gpu = self._get("gpu")
            if isinstance(gpu, list) and gpu:
                card = gpu[0]
                metrics["gpu_utilization"] = float(card.get("proc", 0.0) or card.get("gpu_util", 0.0))
                metrics["gpu_vram_used"] = float(card.get("mem", 0.0) or card.get("memory_used", 0.0))
                metrics["gpu_vram_total"] = float(card.get("mem_total", 0.0) or card.get("memory_total", 0.0))
                if metrics["gpu_vram_total"]:
                    metrics["gpu_vram_percent"] = 100.0 * metrics["gpu_vram_used"] / metrics["gpu_vram_total"]
                metrics["gpu_temperature"] = float(card.get("temperature", 0.0)) if card.get("temperature") is not None else None
                metrics["gpu_power"] = float(card.get("power", 0.0)) if card.get("power") is not None else None
        except (URLError, ValueError, KeyError, TypeError, ZeroDivisionError, IndexError):
            pass

        return metrics
