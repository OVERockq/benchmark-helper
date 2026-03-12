from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from benchmark_system.storage.models import BenchmarkMetric, BenchmarkRun, BenchmarkStep


@dataclass
class DatabaseConfig:
    database_url: str = "sqlite:///benchmark.db"


class Database:
    def __init__(self, config: DatabaseConfig | None = None):
        self.config = config or DatabaseConfig()
        self.path = self._resolve_path(self.config.database_url)

    @staticmethod
    def _resolve_path(database_url: str) -> str:
        if database_url.startswith("sqlite:///"):
            return database_url.replace("sqlite:///", "", 1)
        raise ValueError("Only sqlite:/// URLs are supported in this runtime build")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    measurement_id TEXT PRIMARY KEY,
                    process_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    sampling_interval REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS benchmark_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    measurement_id TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    reference TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_steps_measurement ON benchmark_steps(measurement_id);

                CREATE TABLE IF NOT EXISTS benchmark_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    measurement_id TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    cpu REAL,
                    ram REAL,
                    ram_percent REAL,
                    disk_read REAL,
                    disk_write REAL,
                    io_utilization REAL,
                    gpu_utilization REAL,
                    gpu_vram_used REAL,
                    gpu_vram_total REAL,
                    gpu_vram_percent REAL,
                    gpu_temperature REAL,
                    gpu_power REAL,
                    network_rx REAL,
                    network_tx REAL
                );

                CREATE INDEX IF NOT EXISTS idx_metrics_measurement ON benchmark_metrics(measurement_id);
                CREATE INDEX IF NOT EXISTS idx_metrics_measurement_function ON benchmark_metrics(measurement_id, function_name);

                CREATE TABLE IF NOT EXISTS active_collectors (
                    measurement_id TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    PRIMARY KEY (measurement_id, function_name)
                );
                """
            )

    def create_run(self, measurement_id: str, process_name: str, sampling_interval: float) -> BenchmarkRun:
        start_time = datetime.utcnow()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO benchmark_runs (measurement_id, process_name, start_time, sampling_interval) VALUES (?, ?, ?, ?)",
                (measurement_id, process_name, start_time.isoformat(), sampling_interval),
            )
        return BenchmarkRun(measurement_id, process_name, start_time, None, sampling_interval)

    def end_run(self, measurement_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE benchmark_runs SET end_time = ? WHERE measurement_id = ?", (datetime.utcnow().isoformat(), measurement_id))

    def create_step(self, measurement_id: str, function_name: str, reference: str | None = None) -> BenchmarkStep:
        start_time = datetime.utcnow()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO benchmark_steps (measurement_id, function_name, reference, start_time) VALUES (?, ?, ?, ?)",
                (measurement_id, function_name, reference, start_time.isoformat()),
            )
            row_id = cur.lastrowid or 0
        return BenchmarkStep(row_id, measurement_id, function_name, reference, start_time, None)

    def end_step(self, measurement_id: str, function_name: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE benchmark_steps
                SET end_time = ?
                WHERE id = (
                    SELECT id FROM benchmark_steps
                    WHERE measurement_id = ? AND function_name = ? AND end_time IS NULL
                    ORDER BY start_time DESC LIMIT 1
                )
                """,
                (datetime.utcnow().isoformat(), measurement_id, function_name),
            )

    def add_metric(self, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO benchmark_metrics (
                    measurement_id, function_name, timestamp, cpu, ram, ram_percent,
                    disk_read, disk_write, io_utilization,
                    gpu_utilization, gpu_vram_used, gpu_vram_total, gpu_vram_percent,
                    gpu_temperature, gpu_power, network_rx, network_tx
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["measurement_id"],
                    payload["function_name"],
                    payload["timestamp"].isoformat(),
                    payload.get("cpu"),
                    payload.get("ram"),
                    payload.get("ram_percent"),
                    payload.get("disk_read"),
                    payload.get("disk_write"),
                    payload.get("io_utilization"),
                    payload.get("gpu_utilization"),
                    payload.get("gpu_vram_used"),
                    payload.get("gpu_vram_total"),
                    payload.get("gpu_vram_percent"),
                    payload.get("gpu_temperature"),
                    payload.get("gpu_power"),
                    payload.get("network_rx"),
                    payload.get("network_tx"),
                ),
            )

    def _row_to_run(self, row: sqlite3.Row) -> BenchmarkRun:
        return BenchmarkRun(
            measurement_id=row["measurement_id"],
            process_name=row["process_name"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            sampling_interval=row["sampling_interval"],
        )

    def _row_to_step(self, row: sqlite3.Row) -> BenchmarkStep:
        return BenchmarkStep(
            id=row["id"],
            measurement_id=row["measurement_id"],
            function_name=row["function_name"],
            reference=row["reference"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
        )

    def _row_to_metric(self, row: sqlite3.Row) -> BenchmarkMetric:
        return BenchmarkMetric(
            id=row["id"],
            measurement_id=row["measurement_id"],
            function_name=row["function_name"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            cpu=row["cpu"],
            ram=row["ram"],
            ram_percent=row["ram_percent"],
            disk_read=row["disk_read"],
            disk_write=row["disk_write"],
            io_utilization=row["io_utilization"],
            gpu_utilization=row["gpu_utilization"],
            gpu_vram_used=row["gpu_vram_used"],
            gpu_vram_total=row["gpu_vram_total"],
            gpu_vram_percent=row["gpu_vram_percent"],
            gpu_temperature=row["gpu_temperature"],
            gpu_power=row["gpu_power"],
            network_rx=row["network_rx"],
            network_tx=row["network_tx"],
        )

    def get_run(self, measurement_id: str) -> BenchmarkRun | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM benchmark_runs WHERE measurement_id = ?", (measurement_id,)).fetchone()
            return self._row_to_run(row) if row else None

    def list_runs(self) -> list[BenchmarkRun]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM benchmark_runs ORDER BY start_time DESC").fetchall()
            return [self._row_to_run(r) for r in rows]

    def list_steps(self, measurement_id: str) -> list[BenchmarkStep]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM benchmark_steps WHERE measurement_id = ? ORDER BY start_time ASC", (measurement_id,)
            ).fetchall()
            return [self._row_to_step(r) for r in rows]

    def list_metrics(self, measurement_id: str, function_name: str | None = None) -> list[BenchmarkMetric]:
        with self._connect() as conn:
            if function_name:
                rows = conn.execute(
                    "SELECT * FROM benchmark_metrics WHERE measurement_id = ? AND function_name = ? ORDER BY timestamp ASC",
                    (measurement_id, function_name),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM benchmark_metrics WHERE measurement_id = ? ORDER BY timestamp ASC",
                    (measurement_id,),
                ).fetchall()
            return [self._row_to_metric(r) for r in rows]

    def register_collector(self, measurement_id: str, function_name: str, pid: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "REPLACE INTO active_collectors (measurement_id, function_name, pid, started_at) VALUES (?, ?, ?, ?)",
                (measurement_id, function_name, pid, datetime.utcnow().isoformat()),
            )

    def get_collector_pid(self, measurement_id: str, function_name: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT pid FROM active_collectors WHERE measurement_id = ? AND function_name = ?",
                (measurement_id, function_name),
            ).fetchone()
            return int(row["pid"]) if row else None

    def clear_collector(self, measurement_id: str, function_name: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM active_collectors WHERE measurement_id = ? AND function_name = ?",
                (measurement_id, function_name),
            )
