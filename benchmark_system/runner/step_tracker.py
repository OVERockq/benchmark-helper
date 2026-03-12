from __future__ import annotations

import os
import signal
import subprocess
import sys
import uuid
from dataclasses import dataclass

from benchmark_system.monitor.glances_client import GlancesClient
from benchmark_system.monitor.metrics_collector import MetricsCollector
from benchmark_system.storage.database import Database


@dataclass
class RunContext:
    measurement_id: str
    process_name: str
    sampling_interval: float


class StepTracker:
    def __init__(self, db: Database, glances_client: GlancesClient, database_url: str = "sqlite:///benchmark.db", glances_url: str = "http://localhost:61208/api/3"):
        self.db = db
        self.glances = glances_client
        self.database_url = database_url
        self.glances_url = glances_url
        self.collectors: dict[tuple[str, str], MetricsCollector] = {}
        self.current_run: RunContext | None = None

    @staticmethod
    def new_measurement_id() -> str:
        return uuid.uuid4().hex

    def start_run(self, process_name: str, sampling_interval: float) -> RunContext:
        measurement_id = self.new_measurement_id()
        self.db.create_run(measurement_id, process_name, sampling_interval)
        ctx = RunContext(measurement_id, process_name, sampling_interval)
        self.current_run = ctx
        return ctx

    def end_run(self, measurement_id: str) -> None:
        # 모든 단계 종료 및 수집기 정리
        for step in self.db.list_steps(measurement_id):
            self.step_end(measurement_id, step.function_name)
        
        # detached 프로세스가 남아있는 경우 명시적으로 정리
        steps = self.db.list_steps(measurement_id)
        for step in steps:
            pid = self.db.get_collector_pid(measurement_id, step.function_name)
            if pid:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                self.db.clear_collector(measurement_id, step.function_name)
        
        self.db.end_run(measurement_id)
        if self.current_run and self.current_run.measurement_id == measurement_id:
            self.current_run = None

    def step_start(self, measurement_id: str, function_name: str, reference: str | None = None, detached: bool = False) -> None:
        self.db.create_step(measurement_id, function_name, reference)
        run = self.db.get_run(measurement_id)
        interval = run.sampling_interval if run else 1.0

        if detached:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "benchmark_system.runner.sampler_worker",
                    "--database-url",
                    self.database_url,
                    "--glances-url",
                    self.glances_url,
                    "--measurement-id",
                    measurement_id,
                    "--function",
                    function_name,
                    "--interval",
                    str(interval),
                ],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.db.register_collector(measurement_id, function_name, proc.pid)
            return

        collector = MetricsCollector(self.db, self.glances, measurement_id, function_name, interval)
        collector.start()
        self.collectors[(measurement_id, function_name)] = collector

    def step_end(self, measurement_id: str, function_name: str) -> None:
        collector = self.collectors.pop((measurement_id, function_name), None)
        if collector:
            collector.stop()

        pid = self.db.get_collector_pid(measurement_id, function_name)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            self.db.clear_collector(measurement_id, function_name)

        self.db.end_step(measurement_id, function_name)
