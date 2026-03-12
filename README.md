# Benchmark Helper

Ubuntu Linux 환경에서 Glances REST API를 통해 단계별 리소스 사용량을 수집하는 벤치마크 프레임워크입니다.

## 주요 기능

- CLI 제어: `start`, `step-start`, `step-end`, `end`, `report`
- Python 통합 API: 코드 내에서 `benchmark.start/step_start/step_end/end`
- 모니터링: Glances API 기반 CPU/RAM/Disk/GPU/Network 수집
- 저장소: SQLite 기본 저장 (`benchmark.db`)
- 분석: 단계별 + 전체 실행 min/max/avg 집계
- 내보내기: JSON / CSV / Markdown
- 웹 대시보드: FastAPI + Chart.js 시각화 및 다운로드 버튼
- 실행 API: 웹 API로 실행파일/파라미터를 받아 벤치마크 실행

## 설치

**Python 패키지 설치:**
```bash
pip install -r requirements.txt
```

**Glances 설치 (별도 필요):**
```bash
# Ubuntu/Debian
sudo apt-get install glances

# 또는 pip로
pip install glances
```

## 환경 변수

`.env.example`를 복사해 `.env`로 사용하세요.

```bash
cp .env.example .env
```

지원 변수:

- `BENCHMARK_DATABASE_URL` (기본: `sqlite:///benchmark.db`)
- `BENCHMARK_GLANCES_URL` (기본: `http://localhost:61208/api/3`)
- `BENCHMARK_DEFAULT_INTERVAL` (기본: `1.0`)

## 사전 요구사항

### Glances 설치 및 실행

Glances는 시스템 리소스 모니터링 도구입니다. 벤치마크 실행 전에 설치하고 실행해야 합니다.

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install glances
```

**또는 pip로 설치:**
```bash
pip install glances
```

**Glances 웹 서버 실행:**
```bash
glances -w
```

기본적으로 `http://localhost:61208`에서 실행됩니다. 다른 포트를 사용하려면:
```bash
glances -w --port 61208
```

**연결 확인:**
```bash
curl http://localhost:61208/api/3/cpu
```

정상적으로 연결되면 JSON 응답이 반환됩니다.

## 빠른 실행 스크립트

```bash
./scripts/quick_start.sh
```

샘플 workload: `scripts/sample_workload.py`

## CLI 예시

```bash
python -m benchmark_system.runner.benchmark_cli start --process mesh_pipeline --interval 1
python -m benchmark_system.runner.benchmark_cli step-start --measurement-id <id> --function tile_generation --reference "tiles=5000 size=24GB"
python -m benchmark_system.runner.benchmark_cli step-end --measurement-id <id> --function tile_generation
python -m benchmark_system.runner.benchmark_cli end --measurement-id <id>
python -m benchmark_system.runner.benchmark_cli report --measurement-id <id> --format md
```

## FastAPI 대시보드

```bash
python -m uvicorn benchmark_system.web.api:app --reload
```

브라우저에서 `http://127.0.0.1:8000` 접속:

- Run 목록 확인
- 차트 확인
- JSON/CSV/Markdown 다운로드
- 실행파일 파라미터 입력 후 API 실행

## 실행 API 예시

```bash
curl -X POST http://127.0.0.1:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "process_name":"mesh_pipeline",
    "executable":"python",
    "args":["scripts/sample_workload.py","--sleep","2"],
    "interval":1.0,
    "function_name":"tile_generation",
    "reference":"tiles=5000 size=24GB"
  }'
```

## Program integration

```python
import benchmark

mid = benchmark.start("mesh_pipeline", interval=1)
benchmark.step_start("tile_generation", measurement_id=mid, reference="tiles=5000 size=24GB")
# run_tile_generation()
benchmark.step_end("tile_generation", measurement_id=mid)
benchmark.end(mid)
```
