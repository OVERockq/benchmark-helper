from __future__ import annotations

import threading
import time
from datetime import datetime

from benchmark_system.monitor.glances_client import GlancesClient
from benchmark_system.storage.database import Database


class MetricsCollector:
    def __init__(
        self,
        db: Database,
        glances: GlancesClient,
        measurement_id: str,
        function_name: str,
        interval: float,
    ):
        self.db = db
        self.glances = glances
        self.measurement_id = measurement_id
        self.function_name = function_name
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval * 2)

    def _run(self) -> None:
        while not self._stop.is_set():
            sample = self.glances.sample()
            payload = {
                "measurement_id": self.measurement_id,
                "function_name": self.function_name,
                "timestamp": datetime.utcnow(),
                **sample,
            }
            self.db.add_metric(payload)
            time.sleep(self.interval)
