import argparse
import csv
import io
import json
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path("/root/liujun/saber/project/CloudTrace")
OUT = ROOT / "processed"
REP = ROOT / "reports"
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_osworld_zip as base  # noqa: E402

DATASET = "xlangai/ubuntu_osworld_verified_trajs"
MIRROR_BASE = f"https://hf-mirror.com/datasets/{DATASET}/resolve/main"


class HttpRangeReader(io.RawIOBase):
    def __init__(self, url, size=None, block_size=1024 * 1024):
        self.url = url
        self.size = int(size) if size else self._probe_size()
        self.block_size = block_size
        self.pos = 0
        self.cache_start = -1
        self.cache = b""
        self.requests = 0
        self.bytes_fetched = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            new_pos = offset
        elif whence == io.SEEK_CUR:
            new_pos = self.pos + offset
        elif whence == io.SEEK_END:
            new_pos = self.size + offset
        else:
            raise ValueError(f"bad whence: {whence}")
        if new_pos < 0:
            raise ValueError("negative seek")
        self.pos = new_pos
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        n = min(n, self.size - self.pos)
        if self.cache_start <= self.pos and self.pos + n <= self.cache_start + len(self.cache):
            offset = self.pos - self.cache_start
            data = self.cache[offset : offset + n]
            self.pos += len(data)
            return data
        fetch_start = self.pos
        fetch_len = max(n, self.block_size)
        fetch_end = min(self.size - 1, fetch_start + fetch_len - 1)
        self.cache = self._fetch(fetch_start, fetch_end)
        self.cache_start = fetch_start
        data = self.cache[:n]
        self.pos += len(data)
        return data

    def _probe_size(self):
        req = Request(self.url, headers={"Range": "bytes=0-0", "User-Agent": "CloudTrace-OSWorld-Range"})
        with urlopen(req, timeout=60) as resp:
            cr = resp.headers.get("Content-Range")
            if cr and "/" in cr:
                return int(cr.rsplit("/", 1)[1])
            length = resp.headers.get("Content-Length")
            if length == "1":
                raise RuntimeError("server did not expose Content-Range for ranged request")
            return int(length)

    def _fetch(self, start, end):
        req = Request(
            self.url,
            headers={
                "Range": f"bytes={start}-{end}",
                "User-Agent": "CloudTrace-OSWorld-Range",
            },
        )
        with urlopen(req, timeout=120) as resp:
            status = getattr(resp, "status", None)
            if status not in (206, None):
                raise RuntimeError(f"server ignored Range header, status={status}")
            data = resp.read()
        self.requests += 1
        self.bytes_fetched += len(data)
        return data


def url_for(path):
    return f"{MIRROR_BASE}/{quote(path, safe='/._-')}"


def parse_zip_fileobj(fileobj, model_name):
    source = "OSWorld-Verified"
    events = []
    runs = []
    with zipfile.ZipFile(fileobj) as zf:
        info_by_name = {i.filename: i for i in zf.infolist()}
        for task_dir in base.task_dirs(zf):
            domain, task_id = task_dir.split("/", 1)
            run_id = f"osworld::{model_name}::{domain}::{task_id}"
            result_txt = base.read_member_text(zf, task_dir + "/result.txt").strip()
            runtime_log = base.read_member_text(zf, task_dir + "/runtime.log")
            log_bytes = len(runtime_log.encode("utf-8"))
            lines = [line for line in base.read_member_text(zf, task_dir + "/traj.jsonl").splitlines() if line.strip()]
            steps = []
            for line in lines:
                try:
                    steps.append(json.loads(line))
                except Exception:
                    continue
            events.append(base.make_event(run_id, source, model_name, domain, task_id, "S0", "setup", "setup", log_bytes=log_bytes, result=result_txt))
            first_response = steps[0].get("response", "") if steps else ""
            events.append(base.make_event(run_id, source, model_name, domain, task_id, "S1", "initial_planning", "goal", response=first_response, log_bytes=log_bytes, result=result_txt))
            error_steps = 0
            for step in steps:
                sid = step.get("step_num", "")
                action = step.get("action") or ""
                response = step.get("response") or ""
                if not isinstance(action, str):
                    action = json.dumps(action, ensure_ascii=False)
                if not isinstance(response, str):
                    response = json.dumps(response, ensure_ascii=False)
                screenshot = step.get("screenshot_file") or ""
                screenshot_bytes = base.member_size(info_by_name, task_dir + "/" + screenshot) if screenshot else 0
                error_proxy = 1 if base.re.search(r"\b(error|failed|exception|traceback)\b", response + " " + action, base.re.I) else 0
                error_steps += error_proxy
                events.append(base.make_event(run_id, source, model_name, domain, task_id, "S2", "screenshot_observation", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                events.append(base.make_event(run_id, source, model_name, domain, task_id, "S3", "context_building", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                events.append(base.make_event(run_id, source, model_name, domain, task_id, "S4", "action_decision", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                events.append(base.make_event(run_id, source, model_name, domain, task_id, "S5", "desktop_actuation", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                events.append(base.make_event(run_id, source, model_name, domain, task_id, "S6", "environment_wait", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                if error_proxy:
                    events.append(base.make_event(run_id, source, model_name, domain, task_id, "S7", "feedback_error_recovery", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
            events.append(base.make_event(run_id, source, model_name, domain, task_id, "S8", "validation", "final", log_bytes=log_bytes, result=result_txt))
            runs.append(
                {
                    "run_id": run_id,
                    "source": source,
                    "model": model_name,
                    "domain": domain,
                    "task_id": task_id,
                    "steps": len(steps),
                    "result": result_txt,
                    "success": 1 if result_txt in {"1", "1.0", "True", "true"} else 0,
                    "runtime_log_bytes": log_bytes,
                    "screenshot_bytes_total": sum(e["screenshot_bytes"] for e in events if e["run_id"] == run_id and e["stage_id"] == "S2"),
                    "response_tokens_total": sum(base.approx_tokens(s.get("response", "")) for s in steps),
                    "error_steps": error_steps,
                }
            )
    return runs, events


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    parser.add_argument("--size", type=int, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    model = args.model or Path(args.zip_path).stem
    reader = HttpRangeReader(url_for(args.zip_path), size=args.size)
    start = time.time()
    runs, events = parse_zip_fileobj(reader, model)
    elapsed = time.time() - start
    print("runs", len(runs))
    print("events", len(events))
    print("range_requests", reader.requests)
    print("bytes_fetched", reader.bytes_fetched)
    print("elapsed_sec", round(elapsed, 2))
    if args.check_only:
        return
    OUT.mkdir(exist_ok=True)
    REP.mkdir(exist_ok=True)
    stage_rows = base.aggregate_stage(events, model)
    write_csv(OUT / f"osworld_{model}_runs.csv", runs)
    write_csv(OUT / f"osworld_{model}_events.csv", events)
    write_csv(OUT / f"osworld_{model}_stage_resource_summary.csv", stage_rows)
    base.write_report(model, runs, events, stage_rows)
    print("wrote", OUT / f"osworld_{model}_events.csv")


if __name__ == "__main__":
    main()
