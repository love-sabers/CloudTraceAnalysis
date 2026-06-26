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

DATASET = "xlangai/ubuntu_osworld_verified_trajs"
MIRROR_BASE = f"https://hf-mirror.com/datasets/{DATASET}/resolve/main"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(cmd):
    print("+", " ".join(shlex.quote(str(part)) for part in cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def is_done(model):
    paths = [
        OUT / f"osworld_{model}_events.csv",
        OUT / f"osworld_{model}_runs.csv",
        OUT / f"osworld_{model}_stage_resource_summary.csv",
    ]
    return all(path.exists() and path.stat().st_size > 0 for path in paths)


def load_sizes():
    path = ROOT / "raw" / "osworld_tree_top.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {row["path"]: row.get("size") or 0 for row in rows if row.get("path", "").endswith(".zip")}


def main():
    status_path = OUT / "osworld_zip_batch_status.csv"
    rows = read_csv(status_path)
    if not rows:
        print("no status rows")
        return
    fields = list(rows[0].keys())
    sizes = load_sizes()
    ZIP_DIR.mkdir(parents=True, exist_ok=True)

    for row in rows:
        if row.get("status") != "failed":
            continue
        model = row["model"]
        zip_path = row["zip_path"]
        size_bytes = int(row.get("size_bytes") or sizes.get(zip_path) or 0)
        local_zip = ZIP_DIR / Path(zip_path).name
        start = time.time()
        row["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        row["status"] = "retrying"
        row["error"] = ""
        write_csv(status_path, rows, fields)
        try:
            if is_done(model):
                row["status"] = "done"
                row["download_sec"] = row.get("download_sec") or "0.0"
                row["parse_sec"] = row.get("parse_sec") or "0.0"
                continue
            url = f"{MIRROR_BASE}/{quote(zip_path, safe='/._-')}"
            dl0 = time.time()
            result = run(
                [
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
            )
            row["download_sec"] = f"{time.time() - dl0:.1f}"
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "curl failed").strip()[-2000:])
            if size_bytes and local_zip.exists() and local_zip.stat().st_size != size_bytes:
                raise RuntimeError(f"download size mismatch got={local_zip.stat().st_size} expected={size_bytes}")

            parse0 = time.time()
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
            print(f"FAILED retry {model}: {row['error']}", flush=True)
        finally:
            try:
                if local_zip.exists():
                    os.remove(local_zip)
            except OSError as exc:
                row["error"] = (row.get("error", "") + f" delete_failed={exc}")[:2000]
            row["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            row["duration_sec"] = f"{time.time() - start:.1f}"
            write_csv(status_path, rows, fields)


if __name__ == "__main__":
    main()
