from __future__ import annotations

import argparse
import json

from benchmark_system.analytics.metrics_aggregator import MetricsAggregator
from benchmark_system.config.settings import get_settings, load_dotenv
from benchmark_system.monitor.glances_client import GlancesClient
from benchmark_system.runner.step_tracker import StepTracker
from benchmark_system.storage.database import Database, DatabaseConfig


def build_tracker(database_url: str, glances_url: str) -> StepTracker:
    db = Database(DatabaseConfig(database_url=database_url))
    db.create_schema()
    glances = GlancesClient(base_url=glances_url)
    return StepTracker(db, glances, database_url=database_url, glances_url=glances_url)


def parse_args() -> argparse.Namespace:
    settings = get_settings()

    parser = argparse.ArgumentParser(prog="benchmark")
    parser.add_argument("--env-file", default=".env", help="Path to env file")
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--glances-url", default=settings.glances_url)

    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--process", required=True)
    start.add_argument("--interval", type=float, default=settings.default_interval, choices=list(settings.allowed_intervals))

    sstart = sub.add_parser("step-start")
    sstart.add_argument("--measurement-id", required=True)
    sstart.add_argument("--function", required=True)
    sstart.add_argument("--reference", default=None)

    send = sub.add_parser("step-end")
    send.add_argument("--measurement-id", required=True)
    send.add_argument("--function", required=True)

    end = sub.add_parser("end")
    end.add_argument("--measurement-id", required=True)

    report = sub.add_parser("report")
    report.add_argument("--measurement-id", required=True)
    report.add_argument("--format", choices=["json", "csv", "md"], default="json")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv(args.env_file)
    tracker = build_tracker(args.database_url, args.glances_url)

    if args.command == "start":
        run = tracker.start_run(args.process, args.interval)
        print(run.measurement_id)
        return

    if args.command == "step-start":
        tracker.step_start(args.measurement_id, args.function, args.reference, detached=True)
        print("ok")
        return

    if args.command == "step-end":
        tracker.step_end(args.measurement_id, args.function)
        print("ok")
        return

    if args.command == "end":
        tracker.end_run(args.measurement_id)
        print("ok")
        return

    if args.command == "report":
        db = tracker.db
        agg = MetricsAggregator(db)
        if args.format == "json":
            print(json.dumps(agg.build_run_report(args.measurement_id), default=str, indent=2))
        elif args.format == "csv":
            print(agg.export_csv(args.measurement_id))
        else:
            print(agg.export_markdown(args.measurement_id))


if __name__ == "__main__":
    main()
