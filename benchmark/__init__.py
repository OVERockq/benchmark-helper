from __future__ import annotations

from benchmark_system.config.settings import get_settings
from benchmark_system.monitor.glances_client import GlancesClient
from benchmark_system.runner.step_tracker import StepTracker
from benchmark_system.storage.database import Database, DatabaseConfig

_settings = get_settings()
_db = Database(DatabaseConfig(_settings.database_url))
_db.create_schema()
_tracker = StepTracker(_db, GlancesClient(_settings.glances_url), _settings.database_url, _settings.glances_url)


def start(process_name: str, interval: float = 1.0) -> str:
    ctx = _tracker.start_run(process_name, interval)
    return ctx.measurement_id


def end(measurement_id: str) -> None:
    _tracker.end_run(measurement_id)


def step_start(function_name: str, measurement_id: str, reference: str | None = None) -> None:
    _tracker.step_start(measurement_id, function_name, reference)


def step_end(function_name: str, measurement_id: str) -> None:
    _tracker.step_end(measurement_id, function_name)
