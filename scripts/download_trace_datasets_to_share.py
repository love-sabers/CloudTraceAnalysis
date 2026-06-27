#!/usr/bin/env python3
"""Download raw trace datasets into the shared raw data directory.

This script only writes dataset/raw artifacts under ROOT/raw. It does not move
scripts, reports, or processed outputs.
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote


ROOT = Path("/root/liujun/saber/project/CloudTrace")
RAW = ROOT / "raw"
STATUS = RAW / "trace_dataset_download_status.csv"

ARB_MIRROR = "https://hf-mirror.com/datasets/McGill-NLP/agent-reward-bench/resolve/main"
OSWORLD_MIRROR = "https://hf-mirror.com/datasets/xlangai/ubuntu_osworld_verified_trajs/resolve/main"

STATUS_FIELDS = [
    "dataset",
    "item",
    "target_path",
    "expected_bytes",
    "actual_bytes",
    "status",
    "started_at",
    "finished_at",
    "duration_sec",
    "error",
]


def ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class StatusWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows: list[dict[str, object]] = []
        self.lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, row: dict[str, object]) -> dict[str, object]:
        with self.lock:
            self.rows.append(row)
            self.write_locked()
        return row

    def update(self, row: dict[str, object], **updates: object) -> None:
        with self.lock:
            row.update(updates)
            self.write_locked()

    def write_locked(self) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=STATUS_FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)


def run_curl(url: str, target: Path, expected_bytes: int | None, timeout: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "curl",
        "-4",
        "-L",
        "--fail",
        "--connect-timeout",
        "30",
        "--max-time",
        str(timeout),
        "--retry",
        "6",
        "--retry-delay",
        "10",
        "-C",
        "-",
        "-o",
        str(target),
        url,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "curl failed").strip()[-1200:])
    if expected_bytes and target.exists() and target.stat().st_size != expected_bytes:
        raise RuntimeError(f"size mismatch: expected {expected_bytes}, got {target.stat().st_size}")


def download_item(writer: StatusWriter, dataset: str, item: str, url: str, target: Path, expected_bytes: int | None, timeout: int) -> None:
    start = time.time()
    row = writer.add(
        {
            "dataset": dataset,
            "item": item,
            "target_path": str(target),
            "expected_bytes": expected_bytes or "",
            "actual_bytes": target.stat().st_size if target.exists() else 0,
            "status": "pending",
            "started_at": ts(),
            "finished_at": "",
            "duration_sec": "",
            "error": "",
        }
    )
    try:
        if target.exists() and expected_bytes and target.stat().st_size == expected_bytes:
            writer.update(row, status="skipped_exists", actual_bytes=target.stat().st_size)
            return
        if target.exists() and not expected_bytes and target.stat().st_size > 0:
            writer.update(row, status="skipped_exists", actual_bytes=target.stat().st_size)
            return
        writer.update(row, status="downloading")
        run_curl(url, target, expected_bytes, timeout)
        writer.update(row, status="done", actual_bytes=target.stat().st_size if target.exists() else 0)
    except Exception as exc:
        writer.update(row, status="failed", actual_bytes=target.stat().st_size if target.exists() else 0, error=str(exc).replace("\n", " ")[:1200])
    finally:
        writer.update(row, finished_at=ts(), duration_sec=f"{time.time() - start:.1f}")


def copy_tau(writer: StatusWriter) -> None:
    src = ROOT / "p0_sources" / "tau-bench" / "historical_trajectories"
    dst = RAW / "tau_bench" / "historical_trajectories"
    start = time.time()
    row = writer.add(
        {
            "dataset": "tau-bench",
            "item": "historical_trajectories",
            "target_path": str(dst),
            "expected_bytes": "",
            "actual_bytes": "",
            "status": "pending",
            "started_at": ts(),
            "finished_at": "",
            "duration_sec": "",
            "error": "",
        }
    )
    try:
        if not src.exists():
            raise RuntimeError(f"missing source {src}")
        dst.mkdir(parents=True, exist_ok=True)
        count = 0
        total = 0
        for path in src.glob("*.json"):
            target = dst / path.name
            shutil.copy2(path, target)
            count += 1
            total += target.stat().st_size
        writer.update(row, status="done", actual_bytes=total, error=f"files={count}")
    except Exception as exc:
        writer.update(row, status="failed", error=str(exc).replace("\n", " ")[:1200])
    finally:
        writer.update(row, finished_at=ts(), duration_sec=f"{time.time() - start:.1f}")


def arb_items() -> list[tuple[str, str, Path, int | None]]:
    ann = ROOT / "p0_sources" / "agent-reward-bench" / "agent_reward_bench" / "data" / "annotations.csv"
    if not ann.exists():
        return []
    seen = set()
    out = []
    with ann.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rel = f"cleaned/{row['benchmark']}/{row['model_name']}/{row['exp_name']}/{row['task_id']}.json"
            if rel in seen:
                continue
            seen.add(rel)
            url = f"{ARB_MIRROR}/{quote(rel, safe='/._-')}"
            target = RAW / "agent_reward_bench" / rel
            out.append((rel, url, target, None))
    return out


def osworld_items() -> list[tuple[str, str, Path, int | None]]:
    status = ROOT / "processed" / "osworld_zip_batch_status.csv"
    if not status.exists():
        return []
    out = []
    with status.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            zip_path = row.get("zip_path") or ""
            if not zip_path.endswith(".zip"):
                continue
            size = int(float(row.get("size_bytes") or 0)) or None
            url = f"{OSWORLD_MIRROR}/{quote(zip_path, safe='/._-')}"
            target = RAW / "osworld" / "zips" / Path(zip_path).name
            out.append((zip_path, url, target, size))
    return out


def run_downloads(writer: StatusWriter, dataset: str, items: list[tuple[str, str, Path, int | None]], workers: int, timeout: int, limit: int | None) -> None:
    if limit:
        items = items[:limit]
    if not items:
        return
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(download_item, writer, dataset, item, url, target, expected_bytes, timeout)
            for item, url, target, expected_bytes in items
        ]
        for future in as_completed(futures):
            future.result()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="tau,arb,osworld")
    parser.add_argument("--arb-workers", type=int, default=8)
    parser.add_argument("--osworld-workers", type=int, default=2)
    parser.add_argument("--arb-limit", type=int, default=None)
    parser.add_argument("--osworld-limit", type=int, default=None)
    parser.add_argument("--arb-timeout", type=int, default=900)
    parser.add_argument("--osworld-timeout", type=int, default=28800)
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    writer = StatusWriter(STATUS)
    sources = {x.strip() for x in args.sources.split(",") if x.strip()}
    print(f"RAW={RAW.resolve()}", flush=True)
    if "tau" in sources:
        copy_tau(writer)
    if "arb" in sources:
        items = arb_items()
        print(f"AgentRewardBench items={len(items)}", flush=True)
        run_downloads(writer, "AgentRewardBench", items, args.arb_workers, args.arb_timeout, args.arb_limit)
    if "osworld" in sources:
        items = osworld_items()
        print(f"OSWorld zip items={len(items)}", flush=True)
        run_downloads(writer, "OSWorld", items, args.osworld_workers, args.osworld_timeout, args.osworld_limit)
    print(f"wrote {STATUS}", flush=True)


if __name__ == "__main__":
    main()
