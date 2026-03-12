from __future__ import annotations

import argparse
import hashlib
import time


def cpu_burst(rounds: int) -> None:
    payload = b"benchmark-helper"
    for _ in range(rounds):
        payload = hashlib.sha256(payload).digest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=2.0)
    parser.add_argument("--cpu-rounds", type=int, default=200000)
    args = parser.parse_args()

    cpu_burst(args.cpu_rounds)
    time.sleep(args.sleep)


if __name__ == "__main__":
    main()
