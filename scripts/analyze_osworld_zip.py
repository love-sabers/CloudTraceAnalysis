import argparse
import ast
import csv
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/root/liujun/saber/project/CloudTrace")
OUT = ROOT / "processed"
REP = ROOT / "reports"

RESOURCE_COLS = [
    "accelerator_gpu_npu",
    "cpu",
    "dram_hbm_memory",
    "storage_io",
    "network_io",
    "browser_display_graphics",
    "vm_container_isolation",
]

STAGES = {
    "S0": "setup",
    "S1": "goal_interpretation_planning",
    "S2": "observation_capture",
    "S3": "context_building",
    "S4": "action_decision",
    "S5": "actuation_desktop_gui",
    "S6": "environment_result_wait",
    "S7": "feedback_error_recovery",
    "S8": "validation_finalization",
}

OSWORLD_DOMAINS = {
    "chrome",
    "gimp",
    "libreoffice_calc",
    "libreoffice_impress",
    "libreoffice_writer",
    "multi_apps",
    "os",
    "thunderbird",
    "vlc",
    "vs_code",
}


def approx_tokens(text):
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False)
    return max(1, (len(text or "") + 3) // 4) if text else 0


def resource(stage_id, action_type=None, response_tokens=0, screenshot_bytes=0, log_bytes=0):
    vals = {c: 0 for c in RESOURCE_COLS}
    if stage_id == "S0":
        vals.update(cpu=3, dram_hbm_memory=2, storage_io=2, network_io=1, browser_display_graphics=3, vm_container_isolation=3)
    elif stage_id == "S1":
        vals.update(accelerator_gpu_npu=3, cpu=1, dram_hbm_memory=3)
    elif stage_id == "S2":
        vals.update(accelerator_gpu_npu=2, cpu=2, dram_hbm_memory=2, storage_io=1, browser_display_graphics=3, vm_container_isolation=2)
    elif stage_id == "S3":
        vals.update(accelerator_gpu_npu=2, cpu=3, dram_hbm_memory=3, storage_io=1, browser_display_graphics=2, vm_container_isolation=2)
    elif stage_id == "S4":
        vals.update(accelerator_gpu_npu=3, cpu=1, dram_hbm_memory=3)
    elif stage_id == "S5":
        storage = 2 if action_type in {"file_io", "office_app", "code"} else 1
        cpu = 3 if action_type in {"office_app", "code"} else 2
        vals.update(cpu=cpu, dram_hbm_memory=2, storage_io=storage, network_io=1 if action_type == "browser" else 0, browser_display_graphics=3, vm_container_isolation=3)
    elif stage_id == "S6":
        vals.update(cpu=3, dram_hbm_memory=2, storage_io=2, network_io=1 if action_type == "browser" else 0, browser_display_graphics=3, vm_container_isolation=3)
    elif stage_id == "S7":
        vals.update(accelerator_gpu_npu=3, cpu=2, dram_hbm_memory=3, storage_io=1, browser_display_graphics=2, vm_container_isolation=2)
    elif stage_id == "S8":
        vals.update(accelerator_gpu_npu=1, cpu=3, dram_hbm_memory=1, storage_io=2, network_io=1, browser_display_graphics=1, vm_container_isolation=3)
    if response_tokens > 1000:
        vals["dram_hbm_memory"] = max(vals["dram_hbm_memory"], 3)
    if screenshot_bytes > 250_000:
        vals["dram_hbm_memory"] = max(vals["dram_hbm_memory"], 3 if stage_id in {"S2", "S3"} else vals["dram_hbm_memory"])
        vals["browser_display_graphics"] = max(vals["browser_display_graphics"], 3)
    if log_bytes > 8000:
        vals["cpu"] = max(vals["cpu"], 3)
        vals["storage_io"] = max(vals["storage_io"], 2)
    return vals


def action_type(action, domain):
    if not isinstance(action, str):
        action = json.dumps(action, ensure_ascii=False)
    a = (action or "").lower()
    if action == "DONE" or "agent.exit" in a:
        return "finish"
    if "chrome" in domain or "browser" in a or "http" in a:
        return "browser"
    if "libreoffice" in domain or "writer" in a or "calc" in a or "impress" in a:
        return "office_app"
    if "vscode" in domain or "vs_code" in domain or "code" in a:
        return "code"
    if "open(" in a or "save" in a or "file" in a:
        return "file_io"
    if "pyautogui" in a or "click" in a or "press" in a or "hotkey" in a:
        return "desktop_gui"
    return "desktop_gui"


def task_dirs(zip_file):
    dirs = set()
    for name in zip_file.namelist():
        if name.endswith("/traj.jsonl"):
            parts = name.split("/")
            if len(parts) >= 3:
                dirs.add("/".join(parts[:-1]))
    return sorted(dirs)


def split_task_dir(task_dir):
    parts = task_dir.split("/")
    for i, part in enumerate(parts[:-1]):
        if part in OSWORLD_DOMAINS:
            return part, "/".join(parts[i + 1 :])
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "unknown", task_dir


def read_member_text(zf, name):
    try:
        return zf.read(name).decode("utf-8", errors="replace")
    except KeyError:
        return ""


def member_size(info_by_name, name):
    info = info_by_name.get(name)
    return info.file_size if info else 0


def make_event(run_id, source, model, domain, task_id, stage_id, event_type, step_id, action="", response="", screenshot_bytes=0, log_bytes=0, result=None, error_proxy=0):
    if not isinstance(action, str):
        action = json.dumps(action, ensure_ascii=False)
    if not isinstance(response, str):
        response = json.dumps(response, ensure_ascii=False)
    atype = action_type(action, domain)
    rtoks = approx_tokens(response)
    row = {
        "run_id": run_id,
        "source": source,
        "model": model,
        "domain": domain,
        "task_id": task_id,
        "step_id": step_id,
        "stage_id": stage_id,
        "stage_name": STAGES[stage_id],
        "event_type": event_type,
        "action_type": atype,
        "response_tokens_proxy": rtoks,
        "action_bytes": len((action or "").encode("utf-8")),
        "response_bytes": len((response or "").encode("utf-8")),
        "screenshot_bytes": screenshot_bytes,
        "runtime_log_bytes": log_bytes,
        "result": result if result is not None else "",
        "error_proxy": error_proxy,
    }
    row.update(resource(stage_id, atype, rtoks, screenshot_bytes, log_bytes))
    return row


def parse_zip(zip_path, model_name):
    source = "OSWorld-Verified"
    events = []
    runs = []
    with zipfile.ZipFile(zip_path) as zf:
        info_by_name = {i.filename: i for i in zf.infolist()}
        for task_dir in task_dirs(zf):
            domain, task_id = split_task_dir(task_dir)
            run_id = f"osworld::{model_name}::{domain}::{task_id}"
            traj_name = task_dir + "/traj.jsonl"
            result_txt = read_member_text(zf, task_dir + "/result.txt").strip()
            runtime_log = read_member_text(zf, task_dir + "/runtime.log")
            log_bytes = len(runtime_log.encode("utf-8"))
            lines = [line for line in read_member_text(zf, traj_name).splitlines() if line.strip()]
            steps = []
            for line in lines:
                try:
                    steps.append(json.loads(line))
                except Exception:
                    continue
            events.append(make_event(run_id, source, model_name, domain, task_id, "S0", "setup", "setup", log_bytes=log_bytes, result=result_txt))
            first_response = steps[0].get("response", "") if steps else ""
            events.append(make_event(run_id, source, model_name, domain, task_id, "S1", "initial_planning", "goal", response=first_response, log_bytes=log_bytes, result=result_txt))
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
                screenshot_bytes = member_size(info_by_name, task_dir + "/" + screenshot) if screenshot else 0
                error_proxy = 1 if re.search(r"\b(error|failed|exception|traceback)\b", response + " " + action, re.I) else 0
                error_steps += error_proxy
                events.append(make_event(run_id, source, model_name, domain, task_id, "S2", "screenshot_observation", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                events.append(make_event(run_id, source, model_name, domain, task_id, "S3", "context_building", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                events.append(make_event(run_id, source, model_name, domain, task_id, "S4", "action_decision", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                events.append(make_event(run_id, source, model_name, domain, task_id, "S5", "desktop_actuation", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                events.append(make_event(run_id, source, model_name, domain, task_id, "S6", "environment_wait", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
                if error_proxy:
                    events.append(make_event(run_id, source, model_name, domain, task_id, "S7", "feedback_error_recovery", sid, action, response, screenshot_bytes, log_bytes, result_txt, error_proxy))
            events.append(make_event(run_id, source, model_name, domain, task_id, "S8", "validation", "final", log_bytes=log_bytes, result=result_txt))
            runs.append({
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
                "response_tokens_total": sum(approx_tokens(s.get("response", "")) for s in steps),
                "error_steps": error_steps,
            })
    return runs, events


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def aggregate_stage(events, model):
    acc = defaultdict(lambda: {"count": 0, **{c: 0.0 for c in RESOURCE_COLS}})
    for event in events:
        dst = acc[event["stage_id"]]
        dst["count"] += 1
        for col in RESOURCE_COLS:
            dst[col] += float(event[col])
    rows = []
    for sid, sname in STAGES.items():
        data = acc[sid]
        count = data["count"]
        row = {"source": "OSWorld-Verified", "scope": model, "stage_id": sid, "stage_name": sname, "event_count": count}
        for col in RESOURCE_COLS:
            row[col] = round(data[col] / count, 3) if count else 0
        rows.append(row)
    return rows


def write_report(model, runs, events, stage_rows):
    by_domain = defaultdict(list)
    for row in runs:
        by_domain[row["domain"]].append(row)
    summary_rows = []
    for domain, rows in sorted(by_domain.items()):
        n = len(rows)
        summary_rows.append({
            "domain": domain,
            "runs": n,
            "success_rate": round(sum(r["success"] for r in rows) / n, 3),
            "avg_steps": round(sum(r["steps"] for r in rows) / n, 2),
            "avg_screenshot_mb": round(sum(r["screenshot_bytes_total"] for r in rows) / n / 1_000_000, 3),
            "avg_response_tokens": round(sum(r["response_tokens_total"] for r in rows) / n, 1),
            "avg_runtime_log_kb": round(sum(r["runtime_log_bytes"] for r in rows) / n / 1000, 2),
        })
    write_csv(OUT / f"osworld_{model}_run_summary.csv", summary_rows)
    report = [f"# OSWorld-Verified P0 Summary ({model})\n\n"]
    report.append(f"- Runs: {len(runs)}\n")
    report.append(f"- Events: {len(events)}\n")
    if runs:
        report.append(f"- Success rate: {sum(r['success'] for r in runs) / len(runs):.3f}\n")
    else:
        report.append("- Success rate: n/a\n")
    report.append("\n## Domain Summary\n\n")
    if summary_rows:
        fields = list(summary_rows[0].keys())
        report.append("|" + "|".join(fields) + "|\n")
        report.append("|" + "|".join(["---"] * len(fields)) + "|\n")
        for row in summary_rows:
            report.append("|" + "|".join(str(row[f]) for f in fields) + "|\n")
    else:
        report.append("No `traj.jsonl` task directories were recognized in this archive.\n")
    report.append("\n## Interpretation\n\n")
    report.append("- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.\n")
    report.append("- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.\n")
    report.append("- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.\n")
    (REP / f"osworld_{model}_p0_summary.md").write_text("".join(report), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    REP.mkdir(exist_ok=True)
    zip_path = Path(args.zip_path)
    model = args.model or zip_path.stem
    runs, events = parse_zip(zip_path, model)
    stage_rows = aggregate_stage(events, model)
    write_csv(OUT / f"osworld_{model}_runs.csv", runs)
    write_csv(OUT / f"osworld_{model}_events.csv", events)
    write_csv(OUT / f"osworld_{model}_stage_resource_summary.csv", stage_rows)
    write_report(model, runs, events, stage_rows)
    print("runs", len(runs))
    print("events", len(events))
    print("wrote", OUT / f"osworld_{model}_events.csv")


if __name__ == "__main__":
    main()
