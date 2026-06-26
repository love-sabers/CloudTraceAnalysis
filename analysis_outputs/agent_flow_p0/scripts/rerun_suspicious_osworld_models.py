import csv
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path("/root/liujun/saber/project/CloudTrace")
OUT = ROOT / "processed"
REP = ROOT / "reports"
ZIP_DIR = ROOT / "raw" / "osworld" / "zips"
DATASET = "xlangai/ubuntu_osworld_verified_trajs"
MIRROR_BASE = f"https://hf-mirror.com/datasets/{DATASET}/resolve/main"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run(cmd):
    print("+", " ".join(shlex.quote(str(part)) for part in cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    summary_path = OUT / "osworld_all_model_summary.csv"
    status_path = OUT / "osworld_zip_batch_status.csv"
    tree_path = ROOT / "raw" / "osworld_tree_top.json"
    model_rows = read_csv(summary_path)
    status_rows = read_csv(status_path)
    fields = list(status_rows[0].keys())
    size_by_path = {
        row["path"]: row.get("size") or 0
        for row in json.loads(tree_path.read_text(encoding="utf-8"))
        if row.get("path", "").endswith(".zip")
    }
    status_by_model = {row["model"]: row for row in status_rows}

    suspicious = []
    for row in model_rows:
        runs = int(row.get("runs") or 0)
        events = int(row.get("events") or 0)
        if runs < 300 or events < 1000:
            suspicious.append(row["model"])

    print("suspicious", len(suspicious), suspicious, flush=True)
    ZIP_DIR.mkdir(parents=True, exist_ok=True)

    for model in suspicious:
        status = status_by_model.get(model)
        if not status:
            print("missing status", model, flush=True)
            continue
        zip_path = status["zip_path"]
        size_bytes = int(status.get("size_bytes") or size_by_path.get(zip_path) or 0)
        local_zip = ZIP_DIR / Path(zip_path).name
        start = time.time()
        status["status"] = "rerunning_suspicious"
        status["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        status["error"] = ""
        write_csv(status_path, status_rows, fields)
        try:
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
            status["download_sec"] = f"{time.time() - dl0:.1f}"
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "curl failed").strip()[-2000:])
            if size_bytes and local_zip.exists() and local_zip.stat().st_size != size_bytes:
                raise RuntimeError(f"download size mismatch got={local_zip.stat().st_size} expected={size_bytes}")

            parse0 = time.time()
            result = run(["python3", "scripts/analyze_osworld_zip.py", str(local_zip), "--model", model])
            status["parse_sec"] = f"{time.time() - parse0:.1f}"
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout or "parser failed").strip()[-2000:])

            stage_csv = OUT / f"osworld_{model}_stage_resource_summary.csv"
            heatmap = REP / f"osworld_{model}_stage_resource_heatmap.svg"
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
            status["status"] = "done"
        except Exception as exc:
            status["status"] = "failed"
            status["error"] = str(exc).replace("\n", " ")[:2000]
            print("FAILED suspicious rerun", model, status["error"], flush=True)
        finally:
            try:
                if local_zip.exists():
                    os.remove(local_zip)
            except OSError as exc:
                status["error"] = (status.get("error", "") + f" delete_failed={exc}")[:2000]
            status["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            status["duration_sec"] = f"{time.time() - start:.1f}"
            write_csv(status_path, status_rows, fields)

    result = run(["python3", "scripts/aggregate_osworld_results.py"])
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "aggregate failed")[-2000:])
    result = run(["python3", "scripts/merge_p0_results.py"])
    if result.returncode != 0:
        raise SystemExit((result.stderr or result.stdout or "merge failed")[-2000:])


if __name__ == "__main__":
    main()
