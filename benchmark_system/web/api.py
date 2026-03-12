from __future__ import annotations

import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from benchmark_system.analytics.metrics_aggregator import MetricsAggregator
from benchmark_system.config.settings import get_settings
from benchmark_system.monitor.glances_client import GlancesClient
from benchmark_system.runner.step_tracker import StepTracker
from benchmark_system.storage.database import Database, DatabaseConfig

settings = get_settings()
app = FastAPI(title="Benchmark System")
db = Database(DatabaseConfig(settings.database_url))
db.create_schema()
agg = MetricsAggregator(db)
tracker = StepTracker(db, GlancesClient(settings.glances_url), settings.database_url, settings.glances_url)


class ExecuteRequest(BaseModel):
    process_name: str = Field(..., description="Logical process name for benchmark run")
    executable: str = Field(..., description="Executable path or command")
    args: list[str] = Field(default_factory=list)
    interval: float = Field(default=settings.default_interval)
    function_name: str = Field(default="external_command")
    reference: str | None = Field(default=None)
    timeout_seconds: int | None = Field(default=None)
    cwd: str | None = Field(default=None)


@app.get("/api/runs")
def list_runs() -> list[dict]:
    runs = db.list_runs()
    return [
        {
            "measurement_id": r.measurement_id,
            "process_name": r.process_name,
            "start_time": r.start_time,
            "end_time": r.end_time,
            "sampling_interval": r.sampling_interval,
        }
        for r in runs
    ]


@app.get("/api/runs/{measurement_id}")
def run_report(measurement_id: str) -> dict:
    try:
        report = agg.build_run_report(measurement_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    metrics = db.list_metrics(measurement_id)
    report["series"] = [
        {
            "timestamp": m.timestamp,
            "function_name": m.function_name,
            "cpu": m.cpu,
            "ram": m.ram,
            "disk_read": m.disk_read,
            "disk_write": m.disk_write,
            "gpu_utilization": m.gpu_utilization,
            "gpu_vram_percent": m.gpu_vram_percent,
            "network_rx": m.network_rx,
            "network_tx": m.network_tx,
        }
        for m in metrics
    ]
    return report


@app.get("/api/runs/{measurement_id}/export/{fmt}")
def export_run(measurement_id: str, fmt: str):
    try:
        filename = f"benchmark_{measurement_id}.{fmt if fmt != 'markdown' else 'md'}"
        if fmt == "json":
            body = agg.build_run_report(measurement_id)
            return JSONResponse(body, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
        if fmt == "csv":
            return PlainTextResponse(
                agg.export_csv(measurement_id),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        if fmt in {"md", "markdown"}:
            return PlainTextResponse(
                agg.export_markdown(measurement_id),
                media_type="text/markdown",
                headers={"Content-Disposition": f'attachment; filename="benchmark_{measurement_id}.md"'},
            )
        raise HTTPException(status_code=400, detail="format must be json|csv|md")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/execute")
def execute_benchmark(payload: ExecuteRequest) -> dict:
    if payload.interval not in settings.allowed_intervals:
        raise HTTPException(status_code=400, detail=f"interval must be one of {settings.allowed_intervals}")

    command = [payload.executable, *payload.args]
    run = tracker.start_run(payload.process_name, payload.interval)
    tracker.step_start(run.measurement_id, payload.function_name, payload.reference, detached=True)

    started = datetime.utcnow()
    return_code = -1
    stdout = ""
    stderr = ""
    try:
        completed = subprocess.run(
            command,
            cwd=payload.cwd,
            capture_output=True,
            text=True,
            timeout=payload.timeout_seconds,
            check=False,
        )
        return_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        return_code = -1
        stdout = exc.stdout.decode("utf-8") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    except (FileNotFoundError, PermissionError, OSError) as exc:
        return_code = -1
        stderr = str(exc)
    finally:
        tracker.step_end(run.measurement_id, payload.function_name)
        tracker.end_run(run.measurement_id)

    return {
        "measurement_id": run.measurement_id,
        "process_name": payload.process_name,
        "command": shlex.join(command),
        "started_at": started,
        "ended_at": datetime.utcnow(),
        "return_code": return_code,
        "stdout": stdout,
        "stderr": stderr,
        "report_url": f"/api/runs/{run.measurement_id}",
    }


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    dashboard_path = Path(__file__).parent / "dashboard.html"
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return f.read()


app.mount("/static", StaticFiles(directory=str(Path("benchmark_system/web"))), name="static")
