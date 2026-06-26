import argparse
import csv
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path("/root/liujun/saber/project/CloudTrace")
RAW = ROOT / "raw" / "osworld"
ZIP_DIR = RAW / "zips"
OUT = ROOT / "processed"
REP = ROOT / "reports"
LOG_DIR = ROOT / "logs"

DATASET = "xlangai/ubuntu_osworld_verified_trajs"
MIRROR_BASE = f"https://hf-mirror.com/datasets/{DATASET}/resolve/main"


def write_status(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "model",
        "zip_path",
        "size_bytes",
        "status",
        "started_at",
        "finished_at",
        "duration_sec",
        "download_sec",
        "parse_sec",
        "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(cmd, cwd=ROOT):
    print("+", " ".join(shlex.quote(str(x)) for x in cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def is_done(model):
    required = [
        OUT / f"osworld_{model}_events.csv",
        OUT / f"osworld_{model}_runs.csv",
        OUT / f"osworld_{model}_stage_resource_summary.csv",
    ]
    return all(path.exists() and path.stat().st_size > 0 for path in required)


def load_zips(tree_path):
    data = json.loads(Path(tree_path).read_text(encoding="utf-8"))
    zips = [row for row in data if row.get("path", "").endswith(".zip")]
    return sorted(zips, key=lambda row: (row.get("size") or 0, row.get("path") or ""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", default=str(ROOT / "raw" / "osworld_tree_top.json"))
    parser.add_argument("--status", default=str(OUT / "osworld_zip_batch_status.csv"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    zips = load_zips(args.tree)
    if args.limit is not None:
        zips = zips[: args.limit]

    print(f"OSWorld zip count={len(zips)}", flush=True)
    print(f"planned bytes={sum(row.get('size') or 0 for row in zips)}", flush=True)

    for item in zips:
        zip_path = item["path"]
        model = Path(zip_path).stem
        size_bytes = item.get("size") or 0
        started = time.strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "model": model,
            "zip_path": zip_path,
            "size_bytes": size_bytes,
            "status": "pending",
            "started_at": started,
            "finished_at": "",
            "duration_sec": "",
            "download_sec": "",
            "parse_sec": "",
            "error": "",
        }
        rows.append(row)
        write_status(Path(args.status), rows)

        if is_done(model) and not args.force:
            row["status"] = "skipped_done"
            row["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            row["duration_sec"] = "0.0"
            write_status(Path(args.status), rows)
            print(f"SKIP done {model}", flush=True)
            continue

        if args.dry_run:
            row["status"] = "dry_run"
            row["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            row["duration_sec"] = "0.0"
            write_status(Path(args.status), rows)
            print(f"DRY {model} {size_bytes}", flush=True)
            continue

        local_zip = ZIP_DIR / Path(zip_path).name
        url = f"{MIRROR_BASE}/{quote(zip_path, safe='/._-')}"
        t0 = time.time()
        try:
            if not local_zip.exists() or local_zip.stat().st_size != size_bytes:
                dl0 = time.time()
                row["status"] = "downloading"
                write_status(Path(args.status), rows)
                cmd = [
                    "curl",
                    "-4",
                    "-L",
                    "--fail",
                    "--connect-timeout",
                    "30",
                    "--max-time",
                    "14400",
                    "--retry",
                    "4",
                    "--retry-delay",
                    "10",
                    "-o",
                    str(local_zip),
                    url,
                ]
                result = run(cmd)
                row["download_sec"] = f"{time.time() - dl0:.1f}"
                if result.returncode != 0:
                    raise RuntimeError((result.stderr or result.stdout or "curl failed").strip()[-2000:])
            else:
                row["download_sec"] = "0.0"

            parse0 = time.time()
            row["status"] = "parsing"
            write_status(Path(args.status), rows)
            result = run(["python3", "scripts/analyze_osworld_zip.py", str(local_zip), "--model", model])
            row["parse_sec"] = f"{time.time() - parse0:.1f}"
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "parser failed").strip()[-2000:])

            stage_csv = OUT / f"osworld_{model}_stage_resource_summary.csv"
            heatmap = REP / f"osworld_{model}_stage_resource_heatmap.svg"
            if stage_csv.exists():
                result = run(
                    [
                        "python3",
                        "scripts/generate_stage_heatmap.py",
                        str(stage_csv),
                        str(heatmap),
                        "--title",
                        f"OSWorld {model} stage-resource proxy heatmap",
                    ]
                )
                if result.returncode != 0:
                    print("heatmap warning:", (result.stderr or result.stdout).strip()[-1000:], flush=True)

            row["status"] = "done"
        except Exception as exc:
            row["status"] = "failed"
            row["error"] = str(exc).replace("\n", " ")[:2000]
            print(f"FAILED {model}: {row['error']}", flush=True)
        finally:
            try:
                if local_zip.exists():
                    os.remove(local_zip)
            except OSError as exc:
                row["error"] = (row["error"] + f" delete_failed={exc}")[:2000]
            row["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            row["duration_sec"] = f"{time.time() - t0:.1f}"
            write_status(Path(args.status), rows)


if __name__ == "__main__":
    main()
