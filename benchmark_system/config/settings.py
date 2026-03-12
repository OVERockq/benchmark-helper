from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    database_url: str = "sqlite:///benchmark.db"
    glances_url: str = "http://localhost:61208/api/3"
    default_interval: float = 1.0
    allowed_intervals: tuple[float, ...] = (0.5, 1.0, 2.0, 5.0)


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_settings() -> Settings:
    load_dotenv()
    interval = float(os.getenv("BENCHMARK_DEFAULT_INTERVAL", "1.0"))
    return Settings(
        database_url=os.getenv("BENCHMARK_DATABASE_URL", "sqlite:///benchmark.db"),
        glances_url=os.getenv("BENCHMARK_GLANCES_URL", "http://localhost:61208/api/3"),
        default_interval=interval,
    )
