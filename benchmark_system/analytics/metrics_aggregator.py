from __future__ import annotations

import csv
import io
from statistics import mean
from typing import Any

from benchmark_system.storage.database import Database


METRIC_FIELDS = [
    "cpu",
    "ram",
    "ram_percent",
    "disk_read",
    "disk_write",
    "io_utilization",
    "gpu_utilization",
    "gpu_vram_used",
    "gpu_vram_total",
    "gpu_vram_percent",
    "network_rx",
    "network_tx",
]


class MetricsAggregator:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _stats(values: list[float]) -> dict[str, float | None]:
        if not values:
            return {"min": None, "max": None, "avg": None}
        return {"min": min(values), "max": max(values), "avg": mean(values)}

    def summarize_metrics(self, metrics: list[Any]) -> dict[str, dict[str, float | None]]:
        summary: dict[str, dict[str, float | None]] = {}
        for field in METRIC_FIELDS:
            values = [getattr(m, field) for m in metrics if getattr(m, field) is not None]
            summary[field] = self._stats(values)
        return summary

    def build_run_report(self, measurement_id: str) -> dict[str, Any]:
        run = self.db.get_run(measurement_id)
        if not run:
            raise ValueError(f"measurement_id {measurement_id} not found")
        steps = self.db.list_steps(measurement_id)
        all_metrics = self.db.list_metrics(measurement_id)

        step_reports: list[dict[str, Any]] = []
        for step in steps:
            step_metrics = self.db.list_metrics(measurement_id, step.function_name)
            step_reports.append(
                {
                    "function_name": step.function_name,
                    "reference": step.reference,
                    "start_time": step.start_time,
                    "end_time": step.end_time,
                    "summary": self.summarize_metrics(step_metrics),
                }
            )

        return {
            "measurement_id": run.measurement_id,
            "process_name": run.process_name,
            "start_time": run.start_time,
            "end_time": run.end_time,
            "sampling_interval": run.sampling_interval,
            "step_summaries": step_reports,
            "run_summary": self.summarize_metrics(all_metrics),
            "total_samples": len(all_metrics),
        }

    def export_csv(self, measurement_id: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["measurement_id", "function_name", "timestamp", *METRIC_FIELDS])
        for metric in self.db.list_metrics(measurement_id):
            writer.writerow([
                metric.measurement_id,
                metric.function_name,
                metric.timestamp,
                *[getattr(metric, field) for field in METRIC_FIELDS],
            ])
        return output.getvalue()

    def export_markdown(self, measurement_id: str) -> str:
        report = self.build_run_report(measurement_id)
        lines = [
            f"# Benchmark Report `{report['measurement_id']}`",
            "",
            f"- Process: **{report['process_name']}**",
            f"- Sampling interval: **{report['sampling_interval']} s**",
            f"- Total samples: **{report['total_samples']}**",
            "",
            "## Run summary",
            "",
            "| Metric | Min | Avg | Max |",
            "|---|---:|---:|---:|",
        ]
        for metric, stats in report["run_summary"].items():
            lines.append(f"| {metric} | {stats['min']} | {stats['avg']} | {stats['max']} |")

        lines.append("\n## Step summaries\n")
        for step in report["step_summaries"]:
            lines.append(f"### {step['function_name']}")
            if step["reference"]:
                lines.append(f"Reference: `{step['reference']}`")
            lines.append("| Metric | Min | Avg | Max |")
            lines.append("|---|---:|---:|---:|")
            for metric, stats in step["summary"].items():
                lines.append(f"| {metric} | {stats['min']} | {stats['avg']} | {stats['max']} |")
            lines.append("")
        return "\n".join(lines)
