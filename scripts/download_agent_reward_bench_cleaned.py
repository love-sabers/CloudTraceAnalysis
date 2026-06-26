import argparse
import csv
import subprocess
from pathlib import Path

ROOT = Path("/root/liujun/saber/project/CloudTrace")
ANN = ROOT / "p0_sources" / "agent-reward-bench" / "agent_reward_bench" / "data" / "annotations.csv"
RAW = ROOT / "raw" / "agent_reward_bench" / "cleaned"
MIRROR_BASE = "https://hf-mirror.com/datasets/McGill-NLP/agent-reward-bench/raw/main"


def safe_name(value):
    return value.replace("/", "_").replace(":", "_")


def iter_unique_rows(limit_per_benchmark=None):
    seen = set()
    counts = {}
    with ANN.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            benchmark = row["benchmark"]
            key = (row["benchmark"], row["model_name"], row["exp_name"], row["task_id"])
            if key in seen:
                continue
            if limit_per_benchmark is not None and counts.get(benchmark, 0) >= limit_per_benchmark:
                continue
            seen.add(key)
            counts[benchmark] = counts.get(benchmark, 0) + 1
            yield row


def remote_relpath(row):
    return f"cleaned/{row['benchmark']}/{row['model_name']}/{row['exp_name']}/{row['task_id']}.json"


def local_path(row):
    return (
        RAW
        / row["benchmark"]
        / row["model_name"]
        / row["exp_name"]
        / f"{safe_name(row['task_id'])}.json"
    )


def download_one(row):
    rel = remote_relpath(row)
    url = f"{MIRROR_BASE}/{rel}"
    dest = local_path(row)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return "exists", dest.stat().st_size, rel
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    cmd = [
        "curl",
        "-4",
        "-L",
        "--fail",
        "--connect-timeout",
        "15",
        "--max-time",
        "180",
        "--retry",
        "2",
        "--retry-delay",
        "2",
        "-o",
        str(tmp),
        url,
    ]
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        if tmp.exists():
            tmp.unlink()
        return "failed", 0, rel + " :: " + proc.stderr[-300:].replace("\n", " ")
    tmp.replace(dest)
    return "downloaded", dest.stat().st_size, rel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-per-benchmark", type=int, default=None)
    args = parser.parse_args()

    rows = list(iter_unique_rows(args.sample_per_benchmark))
    print(f"target_rows={len(rows)}")
    total = 0
    status_counts = {}
    for i, row in enumerate(rows, 1):
        status, size, detail = download_one(row)
        total += size
        status_counts[status] = status_counts.get(status, 0) + 1
        print(f"{i}/{len(rows)} {status} {size} {detail}", flush=True)
    print("status_counts", status_counts)
    print("total_bytes_seen", total)


if __name__ == "__main__":
    main()
