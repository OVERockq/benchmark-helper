from __future__ import annotations

import argparse
import signal
import time
from datetime import datetime

from benchmark_system.monitor.glances_client import GlancesClient
from benchmark_system.storage.database import Database, DatabaseConfig

RUNNING = True


def handle_stop(_signum, _frame):
    global RUNNING
    RUNNING = False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default="sqlite:///benchmark.db")
    parser.add_argument("--glances-url", default="http://localhost:61208/api/3")
    parser.add_argument("--measurement-id", required=True)
    parser.add_argument("--function", required=True)
    parser.add_argument("--interval", type=float, required=True)
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    db = Database(DatabaseConfig(args.database_url))
    db.create_schema()
    glances = GlancesClient(args.glances_url)

    while RUNNING:
        sample = glances.sample()
        db.add_metric(
            {
                "measurement_id": args.measurement_id,
                "function_name": args.function,
                "timestamp": datetime.utcnow(),
                **sample,
            }
        )
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
