#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

DB_URL="${BENCHMARK_DATABASE_URL:-sqlite:///benchmark.db}"
GLANCES_URL="${BENCHMARK_GLANCES_URL:-http://localhost:61208/api/3}"
INTERVAL="${BENCHMARK_DEFAULT_INTERVAL:-1.0}"

echo "[1/5] run start"
MID=$(python -m benchmark_system.runner.benchmark_cli --database-url "$DB_URL" --glances-url "$GLANCES_URL" start --process demo_pipeline --interval "$INTERVAL")
echo "measurement_id=$MID"

echo "[2/5] step start"
python -m benchmark_system.runner.benchmark_cli --database-url "$DB_URL" --glances-url "$GLANCES_URL" step-start --measurement-id "$MID" --function demo_stage --reference "sample workload"

echo "[3/5] execute sample workload"
python scripts/sample_workload.py --sleep 2

echo "[4/5] step end + run end"
python -m benchmark_system.runner.benchmark_cli --database-url "$DB_URL" --glances-url "$GLANCES_URL" step-end --measurement-id "$MID" --function demo_stage
python -m benchmark_system.runner.benchmark_cli --database-url "$DB_URL" --glances-url "$GLANCES_URL" end --measurement-id "$MID"

echo "[5/5] markdown report"
python -m benchmark_system.runner.benchmark_cli --database-url "$DB_URL" --glances-url "$GLANCES_URL" report --measurement-id "$MID" --format md
