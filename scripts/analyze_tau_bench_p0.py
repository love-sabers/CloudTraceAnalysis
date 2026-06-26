import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/root/liujun/saber/project/CloudTrace")
SRC = ROOT / "p0_sources" / "tau-bench" / "historical_trajectories"
OUT = ROOT / "processed"
REP = ROOT / "reports"
OUT.mkdir(parents=True, exist_ok=True)
REP.mkdir(parents=True, exist_ok=True)

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
    "S5": "actuation_tool_call",
    "S6": "environment_result_wait",
    "S7": "feedback_error_recovery",
    "S8": "validation_finalization",
}

# 0=none, 1=low, 2=medium, 3=high. These are proxy demands, not counters.
BASE_RESOURCE = {
    "system_context": dict(accelerator_gpu_npu=3, cpu=1, dram_hbm_memory=3, storage_io=0, network_io=0, browser_display_graphics=0, vm_container_isolation=0),
    "user_observation": dict(accelerator_gpu_npu=2, cpu=1, dram_hbm_memory=2, storage_io=0, network_io=1, browser_display_graphics=0, vm_container_isolation=0),
    "assistant_text": dict(accelerator_gpu_npu=3, cpu=1, dram_hbm_memory=3, storage_io=0, network_io=0, browser_display_graphics=0, vm_container_isolation=0),
    "assistant_tool_decision": dict(accelerator_gpu_npu=3, cpu=1, dram_hbm_memory=3, storage_io=0, network_io=0, browser_display_graphics=0, vm_container_isolation=0),
    "tool_actuation": dict(accelerator_gpu_npu=0, cpu=2, dram_hbm_memory=1, storage_io=1, network_io=3, browser_display_graphics=0, vm_container_isolation=0),
    "tool_result": dict(accelerator_gpu_npu=0, cpu=2, dram_hbm_memory=2, storage_io=1, network_io=3, browser_display_graphics=0, vm_container_isolation=0),
    "error_recovery": dict(accelerator_gpu_npu=3, cpu=2, dram_hbm_memory=3, storage_io=1, network_io=2, browser_display_graphics=0, vm_container_isolation=0),
    "validation": dict(accelerator_gpu_npu=1, cpu=2, dram_hbm_memory=1, storage_io=1, network_io=1, browser_display_graphics=0, vm_container_isolation=0),
}


def approx_tokens(text):
    if text is None:
        return 0
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False)
    return max(1, math.ceil(len(text) / 4)) if text else 0


def tool_calls(msg):
    calls = msg.get("tool_calls")
    if not calls:
        return []
    return calls if isinstance(calls, list) else [calls]


def call_name(call):
    fn = call.get("function") if isinstance(call, dict) else None
    return fn.get("name") if isinstance(fn, dict) and fn.get("name") else ""


def call_args(call):
    fn = call.get("function") if isinstance(call, dict) else None
    return fn.get("arguments") if isinstance(fn, dict) else None


def classify_message(msg):
    role = msg.get("role")
    content = msg.get("content")
    calls = tool_calls(msg)
    content_text = content if isinstance(content, str) else (json.dumps(content, ensure_ascii=False) if content is not None else "")
    lower = content_text.lower()
    is_error = "error" in lower or "not found" in lower or "failed" in lower
    if role == "system":
        return "S1", "system_context", False
    if role == "user":
        return "S2", "user_observation", False
    if role == "assistant" and calls:
        return "S4", "assistant_tool_decision", False
    if role == "assistant":
        if is_error or any(word in lower for word in ["apologize", "couldn't", "please verify", "try again"]):
            return "S7", "error_recovery", True
        return "S4", "assistant_text", False
    if role == "tool":
        if is_error:
            return "S7", "error_recovery", True
        return "S6", "tool_result", False
    return "S3", "assistant_text", False


def bump_by_size(resources, tokens, output_bytes, event_type):
    r = dict(resources)
    if tokens > 2000:
        r["dram_hbm_memory"] = max(r["dram_hbm_memory"], 3)
        r["accelerator_gpu_npu"] = max(r["accelerator_gpu_npu"], 3)
    elif tokens > 800:
        r["dram_hbm_memory"] = max(r["dram_hbm_memory"], 2)
    if output_bytes > 4000:
        r["cpu"] = max(r["cpu"], 2)
        r["dram_hbm_memory"] = max(r["dram_hbm_memory"], 2)
    if event_type in ("tool_result", "tool_actuation") and output_bytes > 8000:
        r["network_io"] = max(r["network_io"], 3)
        r["storage_io"] = max(r["storage_io"], 2)
    return r


def source_from_filename(name):
    stem = name.replace(".json", "")
    domain = "airline" if "airline" in stem else "retail" if "retail" in stem else "unknown"
    if stem.startswith("gpt-4o"):
        model = "gpt-4o"
    elif stem.startswith("sonnet-35"):
        model = "claude-3.5-sonnet"
    else:
        model = stem
    return model, domain


events = []
run_rows = []

for path in sorted(SRC.glob("*.json")):
    model, domain = source_from_filename(path.name)
    data = json.loads(path.read_text())
    for run_idx, run in enumerate(data):
        run_id = f"tau::{model}::{domain}::{run.get('task_id')}::{run.get('trial', run_idx)}::{run_idx}"
        traj = run.get("traj", []) or []
        reward = float(run.get("reward") or 0.0)
        run_counter = Counter()
        for step_id, msg in enumerate(traj):
            stage_id, event_type, retry_flag = classify_message(msg)
            role = msg.get("role") or ""
            content = msg.get("content")
            content_text = content if isinstance(content, str) else (json.dumps(content, ensure_ascii=False) if content is not None else "")
            calls = tool_calls(msg)
            names = [call_name(c) for c in calls]
            args_text = json.dumps([call_args(c) for c in calls], ensure_ascii=False)
            input_tokens_proxy = approx_tokens(content_text) if role in ("system", "user", "tool") else 0
            output_tokens_proxy = approx_tokens(content_text) if role == "assistant" and content_text else 0
            tool_arg_bytes = len(args_text.encode("utf-8")) if calls else 0
            content_bytes = len(content_text.encode("utf-8")) if content_text else 0
            resources = bump_by_size(
                BASE_RESOURCE[event_type],
                input_tokens_proxy + output_tokens_proxy,
                content_bytes + tool_arg_bytes,
                event_type,
            )
            row = {
                "run_id": run_id,
                "source": "tau-bench",
                "model": model,
                "domain": domain,
                "task_id": run.get("task_id"),
                "trial": run.get("trial", run_idx),
                "reward": reward,
                "success": 1 if reward > 0 else 0,
                "step_id": step_id,
                "role": role,
                "stage_id": stage_id,
                "stage_name": STAGES[stage_id],
                "event_type": event_type,
                "tool_call_count": len(calls),
                "tool_names": "|".join(n for n in names if n),
                "content_bytes": content_bytes,
                "tool_arg_bytes": tool_arg_bytes,
                "input_tokens_proxy": input_tokens_proxy,
                "output_tokens_proxy": output_tokens_proxy,
                "retry_or_error_proxy": 1 if retry_flag else 0,
            }
            row.update(resources)
            events.append(row)
            run_counter[event_type] += 1
            run_counter[f"stage_{stage_id}"] += 1
            if calls:
                for call_idx, call in enumerate(calls):
                    nm = call_name(call)
                    arg = call_args(call)
                    arg_text = json.dumps(arg, ensure_ascii=False) if not isinstance(arg, str) else arg
                    arg_bytes = len(arg_text.encode("utf-8"))
                    resources = bump_by_size(BASE_RESOURCE["tool_actuation"], approx_tokens(arg_text), arg_bytes, "tool_actuation")
                    act = {
                        "run_id": run_id,
                        "source": "tau-bench",
                        "model": model,
                        "domain": domain,
                        "task_id": run.get("task_id"),
                        "trial": run.get("trial", run_idx),
                        "reward": reward,
                        "success": 1 if reward > 0 else 0,
                        "step_id": f"{step_id}.{call_idx}",
                        "role": "tool_call",
                        "stage_id": "S5",
                        "stage_name": STAGES["S5"],
                        "event_type": "tool_actuation",
                        "tool_call_count": 1,
                        "tool_names": nm,
                        "content_bytes": 0,
                        "tool_arg_bytes": arg_bytes,
                        "input_tokens_proxy": approx_tokens(arg_text),
                        "output_tokens_proxy": 0,
                        "retry_or_error_proxy": 0,
                    }
                    act.update(resources)
                    events.append(act)
                    run_counter["tool_actuation"] += 1
                    run_counter["stage_S5"] += 1
        validation = {
            "run_id": run_id,
            "source": "tau-bench",
            "model": model,
            "domain": domain,
            "task_id": run.get("task_id"),
            "trial": run.get("trial", run_idx),
            "reward": reward,
            "success": 1 if reward > 0 else 0,
            "step_id": "final",
            "role": "evaluator",
            "stage_id": "S8",
            "stage_name": STAGES["S8"],
            "event_type": "validation",
            "tool_call_count": 0,
            "tool_names": "",
            "content_bytes": 0,
            "tool_arg_bytes": 0,
            "input_tokens_proxy": 0,
            "output_tokens_proxy": 0,
            "retry_or_error_proxy": 0,
        }
        validation.update(BASE_RESOURCE["validation"])
        events.append(validation)
        run_counter["validation"] += 1
        run_counter["stage_S8"] += 1
        run_rows.append({
            "run_id": run_id,
            "source": "tau-bench",
            "model": model,
            "domain": domain,
            "task_id": run.get("task_id"),
            "trial": run.get("trial", run_idx),
            "reward": reward,
            "success": 1 if reward > 0 else 0,
            "traj_messages": len(traj),
            "events_with_actuation": sum(run_counter.values()),
            "tool_actuations": run_counter["tool_actuation"],
            "tool_results": run_counter["tool_result"],
            "error_recovery_events": run_counter["error_recovery"],
            **{f"{sid}_events": run_counter[f"stage_{sid}"] for sid in STAGES},
        })

if not events:
    raise SystemExit(f"No events found in {SRC}")

with (OUT / "tau_events.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(events[0].keys()))
    writer.writeheader()
    writer.writerows(events)

with (OUT / "tau_runs.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(run_rows[0].keys()))
    writer.writeheader()
    writer.writerows(run_rows)

stage_all = defaultdict(lambda: {"count": 0, **{c: 0.0 for c in RESOURCE_COLS}})
for event in events:
    dst = stage_all[event["stage_id"]]
    dst["count"] += 1
    for col in RESOURCE_COLS:
        dst[col] += float(event[col])

summary_rows = []
for stage_id in STAGES:
    data = stage_all[stage_id]
    count = data["count"]
    row = {"source": "tau-bench", "scope": "all", "stage_id": stage_id, "stage_name": STAGES[stage_id], "event_count": count}
    for col in RESOURCE_COLS:
        row[col] = round(data[col] / count, 3) if count else 0
    summary_rows.append(row)

with (OUT / "tau_stage_resource_summary.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
    writer.writeheader()
    writer.writerows(summary_rows)

groups = defaultdict(list)
for row in run_rows:
    groups[(row["model"], row["domain"])].append(row)

run_summary = []
for (model, domain), rows in sorted(groups.items()):
    n = len(rows)

    def avg(key):
        return sum(float(row[key]) for row in rows) / n

    run_summary.append({
        "model": model,
        "domain": domain,
        "runs": n,
        "success_rate": round(avg("success"), 3),
        "avg_traj_messages": round(avg("traj_messages"), 2),
        "avg_tool_actuations": round(avg("tool_actuations"), 2),
        "avg_tool_results": round(avg("tool_results"), 2),
        "avg_error_recovery_events": round(avg("error_recovery_events"), 2),
        **{f"avg_{sid}_events": round(avg(f"{sid}_events"), 2) for sid in STAGES},
    })

with (OUT / "tau_run_summary.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(run_summary[0].keys()))
    writer.writeheader()
    writer.writerows(run_summary)

cell_w, cell_h = 130, 34
left, top = 190, 70
width = left + cell_w * len(RESOURCE_COLS) + 30
height = top + cell_h * len(STAGES) + 70
colors = ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5"]


def color(value):
    return colors[max(0, min(3, int(round(value))))]


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
svg.append('<rect width="100%" height="100%" fill="white"/>')
svg.append('<text x="20" y="30" font-family="Arial" font-size="20" font-weight="700">tau-bench stage-resource proxy heatmap</text>')
svg.append('<text x="20" y="52" font-family="Arial" font-size="12" fill="#555">0=none, 1=low, 2=medium, 3=high; proxy demand from trace events, not direct counters</text>')
for j, col in enumerate(RESOURCE_COLS):
    x = left + j * cell_w + cell_w / 2
    svg.append(f'<text x="{x}" y="{top - 12}" font-family="Arial" font-size="11" text-anchor="middle">{esc(col.replace("_", " "))}</text>')
for i, row in enumerate(summary_rows):
    y = top + i * cell_h
    svg.append(f'<text x="12" y="{y + 22}" font-family="Arial" font-size="12">{row["stage_id"]} {esc(row["stage_name"])}</text>')
    for j, col in enumerate(RESOURCE_COLS):
        x = left + j * cell_w
        value = float(row[col])
        svg.append(f'<rect x="{x}" y="{y}" width="{cell_w - 2}" height="{cell_h - 2}" fill="{color(value)}" stroke="#fff"/>')
        svg.append(f'<text x="{x + cell_w / 2}" y="{y + 21}" font-family="Arial" font-size="12" text-anchor="middle" fill="#111">{value:.2f}</text>')
svg.append("</svg>")
(REP / "tau_stage_resource_heatmap.svg").write_text("\n".join(svg), encoding="utf-8")


def md_table(rows, cols):
    out = ["|" + "|".join(cols) + "|", "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(row.get(col, "")) for col in cols) + "|")
    return "\n".join(out)


report = []
report.append("# tau-bench P0 Agent Flow Trace Summary\n")
report.append("## Dataset Snapshot\n")
report.append("- Source commit: 59a200c6d575d595120f1cb70fea53cef0632f6b\n")
report.append("- Raw files: 4 JSON files, about 50MB.\n")
report.append(f"- Parsed runs: {len(run_rows)}\n")
report.append(f"- Parsed events including synthetic tool-actuation and validation rows: {len(events)}\n")
report.append("\n## Run Summary by Model and Domain\n")
report.append(md_table(run_summary, ["model", "domain", "runs", "success_rate", "avg_traj_messages", "avg_tool_actuations", "avg_error_recovery_events"]))
report.append("\n\n## Stage Resource Proxy Summary\n")
report.append(md_table(summary_rows, ["stage_id", "stage_name", "event_count"] + RESOURCE_COLS))
report.append("\n\n## Interpretation\n")
report.append("- tau-bench is a strict agent-flow source for tool/API conversational agents.\n")
report.append("- The dominant phases alternate between accelerator/HBM-heavy LLM planning and decision stages (S1/S4), and network/API/CPU-heavy tool actuation/result stages (S5/S6).\n")
report.append("- Browser/display and VM/container demand are near zero in this source; this makes tau-bench a useful contrast class against OSWorld and web/GUI agents.\n")
report.append("- Error and recovery events (S7) are resource amplifiers because they re-enter the observe-decide-act loop.\n")
report.append("\n## Artifacts\n")
report.append("- `processed/tau_events.csv`: event-level normalized trace table.\n")
report.append("- `processed/tau_runs.csv`: run-level counters.\n")
report.append("- `processed/tau_run_summary.csv`: model/domain aggregate.\n")
report.append("- `processed/tau_stage_resource_summary.csv`: stage-resource matrix.\n")
report.append("- `reports/tau_stage_resource_heatmap.svg`: image-ready stage-resource heatmap.\n")
(REP / "tau_bench_p0_summary.md").write_text("\n".join(report), encoding="utf-8")

print("events", len(events))
print("runs", len(run_rows))
print("wrote", OUT / "tau_events.csv")
print("wrote", REP / "tau_stage_resource_heatmap.svg")
