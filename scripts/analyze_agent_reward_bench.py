import argparse
import csv
import json
import os
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/root/liujun/saber/project/CloudTrace")
ARB = ROOT / "p0_sources" / "agent-reward-bench"
ANN = ARB / "agent_reward_bench" / "data" / "annotations.csv"
OUT = ROOT / "processed"
REP = ROOT / "reports"
MIRROR_BASE = "https://hf-mirror.com/datasets/McGill-NLP/agent-reward-bench/resolve/main"

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
    "S5": "actuation_browser_gui",
    "S6": "environment_result_wait",
    "S7": "feedback_error_recovery",
    "S8": "validation_finalization",
}


def score(base=None, **overrides):
    row = {col: 0 for col in RESOURCE_COLS}
    if base:
        row.update(base)
    row.update(overrides)
    return row


def label_score(value):
    if not value:
        return ""
    return value.replace("|", "/")


def safe_file(value):
    return value.replace("/", "_").replace(":", "_")


def load_annotations():
    grouped = {}
    with ANN.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["benchmark"], row["model_name"], row["exp_name"], row["task_id"])
            grouped.setdefault(key, []).append(row)
    out = []
    for key, rows in grouped.items():
        benchmark, model_name, exp_name, task_id = key
        success_counts = Counter(r["trajectory_success"] for r in rows)
        looping_counts = Counter(r["trajectory_looping"] for r in rows)
        side_counts = Counter(r["trajectory_side_effect"] for r in rows)
        optimality_counts = Counter(r["trajectory_optimality"] for r in rows)
        out.append({
            "benchmark": benchmark,
            "model_name": model_name,
            "exp_name": exp_name,
            "task_id": task_id,
            "annotation_count": len(rows),
            "human_success_label": success_counts.most_common(1)[0][0],
            "human_looping_label": looping_counts.most_common(1)[0][0],
            "human_side_effect_label": side_counts.most_common(1)[0][0],
            "human_optimality_label": optimality_counts.most_common(1)[0][0],
        })
    return out


def rel_path(row):
    return f"cleaned/{row['benchmark']}/{row['model_name']}/{row['exp_name']}/{row['task_id']}.json"


def download_to_temp(row):
    url = f"{MIRROR_BASE}/{rel_path(row)}"
    fd, tmp_name = tempfile.mkstemp(prefix="arb_", suffix=".json")
    os.close(fd)
    Path(tmp_name).unlink(missing_ok=True)
    cmd = [
        "curl",
        "-4",
        "-L",
        "--fail",
        "--connect-timeout",
        "15",
        "--max-time",
        "240",
        "--retry",
        "2",
        "--retry-delay",
        "2",
        "-o",
        tmp_name,
        url,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        Path(tmp_name).unlink(missing_ok=True)
        raise RuntimeError(proc.stderr[-500:].replace("\n", " "))
    text_start = Path(tmp_name).read_text(errors="replace")[:80]
    if text_start.startswith("version https://git-lfs.github.com/spec"):
        Path(tmp_name).unlink(missing_ok=True)
        raise RuntimeError("downloaded_lfs_pointer")
    return Path(tmp_name)


def action_kind(action):
    a = (action or "").strip().lower()
    if a.startswith("click"):
        return "click"
    if a.startswith("fill") or a.startswith("type"):
        return "text_input"
    if a.startswith("goto") or a.startswith("open") or "http" in a:
        return "navigation"
    if "stop" in a or "answer" in a:
        return "finish"
    if not a:
        return "none"
    return a.split("(", 1)[0][:40]


def resource_for_stage(stage_id, step, data):
    stats = step.get("stats") or {}
    input_tokens = int(stats.get("input_tokens") or 0)
    output_tokens = int(stats.get("output_tokens") or 0)
    axtree_bytes = len((step.get("axtree") or "").encode("utf-8"))
    action = step.get("action") or ""
    action_type = action_kind(action)
    has_error = bool(step.get("last_action_error"))
    use_screenshot = bool((data.get("flags") or {}).get("obs", {}).get("use_screenshot"))
    base = score()
    if stage_id == "S0":
        base = score(cpu=2, dram_hbm_memory=2, storage_io=1, network_io=2, browser_display_graphics=3)
    elif stage_id == "S1":
        base = score(accelerator_gpu_npu=3, cpu=1, dram_hbm_memory=3)
    elif stage_id == "S2":
        base = score(accelerator_gpu_npu=2 if use_screenshot else 0, cpu=2, dram_hbm_memory=2, network_io=2, browser_display_graphics=3)
    elif stage_id == "S3":
        base = score(accelerator_gpu_npu=2 if use_screenshot else 0, cpu=3, dram_hbm_memory=3, network_io=1, browser_display_graphics=2)
    elif stage_id == "S4":
        base = score(accelerator_gpu_npu=3, cpu=1, dram_hbm_memory=3)
    elif stage_id == "S5":
        net = 3 if action_type == "navigation" else 2 if action_type in ("click", "text_input") else 1
        base = score(cpu=2, dram_hbm_memory=1, network_io=net, browser_display_graphics=3)
    elif stage_id == "S6":
        elapsed = float(stats.get("step_elapsed") or stats.get("agent_elapsed") or 0.0)
        cpu = 3 if elapsed > 8 else 2
        base = score(cpu=cpu, dram_hbm_memory=2, network_io=2, browser_display_graphics=3)
    elif stage_id == "S7":
        base = score(accelerator_gpu_npu=3, cpu=2, dram_hbm_memory=3, network_io=2, browser_display_graphics=2)
    elif stage_id == "S8":
        base = score(accelerator_gpu_npu=1, cpu=2, dram_hbm_memory=1, storage_io=1, network_io=1, browser_display_graphics=1)
    if input_tokens > 12000 or axtree_bytes > 250000:
        base["dram_hbm_memory"] = max(base["dram_hbm_memory"], 3)
        base["cpu"] = max(base["cpu"], 3 if stage_id in ("S2", "S3") else base["cpu"])
    if input_tokens > 8000 and stage_id == "S4":
        base["accelerator_gpu_npu"] = 3
        base["dram_hbm_memory"] = 3
    if has_error and stage_id in ("S6", "S7"):
        base["cpu"] = max(base["cpu"], 2)
        base["network_io"] = max(base["network_io"], 2)
    return base


def make_event(row, data, step, stage_id, event_type, step_id):
    stats = step.get("stats") or {}
    resources = resource_for_stage(stage_id, step, data)
    action = step.get("action") or ""
    axtree = step.get("axtree") or ""
    err = step.get("last_action_error") or ""
    ev = {
        "run_id": f"arb::{row['benchmark']}::{row['model_name']}::{row['task_id']}",
        "source": "AgentRewardBench",
        "benchmark": row["benchmark"],
        "model": row["model_name"],
        "exp_name": row["exp_name"],
        "task_id": row["task_id"],
        "human_success_label": label_score(row["human_success_label"]),
        "human_looping_label": label_score(row["human_looping_label"]),
        "human_side_effect_label": label_score(row["human_side_effect_label"]),
        "human_optimality_label": label_score(row["human_optimality_label"]),
        "step_id": step_id,
        "stage_id": stage_id,
        "stage_name": STAGES[stage_id],
        "event_type": event_type,
        "action_type": action_kind(action),
        "input_tokens": int(stats.get("input_tokens") or 0),
        "output_tokens": int(stats.get("output_tokens") or 0),
        "axtree_bytes": len(axtree.encode("utf-8")),
        "reasoning_bytes": len((step.get("reasoning") or "").encode("utf-8")),
        "action_bytes": len(action.encode("utf-8")),
        "last_action_error_bytes": len(err.encode("utf-8")),
        "n_retry_llm": float(stats.get("n_retry_llm") or 0),
        "n_retry": float(stats.get("n_retry") or 0),
        "busted_retry": int(stats.get("busted_retry") or 0),
        "step_elapsed": float(stats.get("step_elapsed") or 0.0),
        "agent_elapsed": float(stats.get("agent_elapsed") or 0.0),
        "url_present": 1 if step.get("url") else 0,
        "screenshot_present": 1 if step.get("screenshot_path") else 0,
        "error_proxy": 1 if err else 0,
    }
    ev.update(resources)
    return ev


def process_run(row, data):
    steps = data.get("steps") or []
    summary = data.get("summary_info") or {}
    events = []
    setup = {"stats": {}, "action": "", "axtree": "", "reasoning": "", "last_action_error": ""}
    events.append(make_event(row, data, setup, "S0", "setup", "setup"))
    goal_step = {"stats": {"input_tokens": summary.get("stats.max_n_token_goal", 0)}, "reasoning": data.get("goal", ""), "action": "", "axtree": ""}
    events.append(make_event(row, data, goal_step, "S1", "goal_planning", "goal"))
    for step in steps:
        sid = step.get("num")
        events.append(make_event(row, data, step, "S2", "observation_capture", sid))
        events.append(make_event(row, data, step, "S3", "context_building", sid))
        events.append(make_event(row, data, step, "S4", "action_decision", sid))
        events.append(make_event(row, data, step, "S5", "browser_gui_actuation", sid))
        events.append(make_event(row, data, step, "S6", "environment_wait", sid))
        if step.get("last_action_error") or float((step.get("stats") or {}).get("n_retry") or 0) > 0:
            events.append(make_event(row, data, step, "S7", "feedback_error_recovery", sid))
    validation = {"stats": {}, "action": "", "axtree": "", "reasoning": "", "last_action_error": summary.get("err_msg") or ""}
    events.append(make_event(row, data, validation, "S8", "validation", "final"))
    run = {
        "run_id": f"arb::{row['benchmark']}::{row['model_name']}::{row['task_id']}",
        "source": "AgentRewardBench",
        "benchmark": row["benchmark"],
        "model": row["model_name"],
        "exp_name": row["exp_name"],
        "task_id": row["task_id"],
        "annotation_count": row["annotation_count"],
        "human_success_label": row["human_success_label"],
        "human_looping_label": row["human_looping_label"],
        "human_side_effect_label": row["human_side_effect_label"],
        "human_optimality_label": row["human_optimality_label"],
        "valid": data.get("valid"),
        "n_steps": len(steps),
        "summary_cum_reward": summary.get("cum_reward"),
        "summary_terminated": summary.get("terminated"),
        "summary_truncated": summary.get("truncated"),
        "cum_input_tokens": summary.get("stats.cum_input_tokens"),
        "cum_output_tokens": summary.get("stats.cum_output_tokens"),
        "cum_step_elapsed": summary.get("stats.cum_step_elapsed"),
        "cum_agent_elapsed": summary.get("stats.cum_agent_elapsed"),
        "cum_dom_tokens": summary.get("stats.cum_n_token_dom_txt"),
        "cum_axtree_tokens": summary.get("stats.cum_n_token_axtree_txt"),
        "cum_pruned_html_tokens": summary.get("stats.cum_n_token_pruned_html"),
        "events": len(events),
        "error_steps": sum(1 for s in steps if s.get("last_action_error")),
    }
    return run, events


def write_heatmap(summary_rows, path, title):
    cell_w, cell_h = 130, 34
    left, top = 190, 70
    width = left + cell_w * len(RESOURCE_COLS) + 30
    height = top + cell_h * len(STAGES) + 70
    colors = ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5"]

    def color(value):
        return colors[max(0, min(3, int(round(float(value)))))]

    def esc(text):
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    by_stage = {r["stage_id"]: r for r in summary_rows}
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    svg.append('<rect width="100%" height="100%" fill="white"/>')
    svg.append(f'<text x="20" y="30" font-family="Arial" font-size="20" font-weight="700">{esc(title)}</text>')
    svg.append('<text x="20" y="52" font-family="Arial" font-size="12" fill="#555">0=none, 1=low, 2=medium, 3=high; proxy demand from trace events, not direct counters</text>')
    for j, col in enumerate(RESOURCE_COLS):
        x = left + j * cell_w + cell_w / 2
        svg.append(f'<text x="{x}" y="{top - 12}" font-family="Arial" font-size="11" text-anchor="middle">{esc(col.replace("_", " "))}</text>')
    for i, stage_id in enumerate(STAGES):
        row = by_stage.get(stage_id, {"stage_id": stage_id, "stage_name": STAGES[stage_id], **{c: 0 for c in RESOURCE_COLS}})
        y = top + i * cell_h
        svg.append(f'<text x="12" y="{y + 22}" font-family="Arial" font-size="12">{stage_id} {esc(STAGES[stage_id])}</text>')
        for j, col in enumerate(RESOURCE_COLS):
            x = left + j * cell_w
            value = float(row[col])
            svg.append(f'<rect x="{x}" y="{y}" width="{cell_w - 2}" height="{cell_h - 2}" fill="{color(value)}" stroke="#fff"/>')
            svg.append(f'<text x="{x + cell_w / 2}" y="{y + 21}" font-family="Arial" font-size="12" text-anchor="middle" fill="#111">{value:.2f}</text>')
    svg.append("</svg>")
    path.write_text("\n".join(svg), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-per-benchmark", type=int, default=None)
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--only-failures-csv", type=str, default=None)
    parser.add_argument("--suffix", type=str, default=None)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    REP.mkdir(parents=True, exist_ok=True)
    if args.only_failures_csv:
        with Path(args.only_failures_csv).open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    else:
        rows = load_annotations()
    if args.limit_per_benchmark is not None:
        counts = Counter()
        filtered = []
        for row in rows:
            if counts[row["benchmark"]] < args.limit_per_benchmark:
                filtered.append(row)
                counts[row["benchmark"]] += 1
        rows = filtered
    if args.max_runs is not None:
        rows = rows[:args.max_runs]

    suffix = args.suffix or ("sample" if args.limit_per_benchmark or args.max_runs else "all")
    events_path = OUT / f"arb_events_{suffix}.csv"
    runs_path = OUT / f"arb_runs_{suffix}.csv"
    fail_path = OUT / f"arb_failed_downloads_{suffix}.csv"

    event_fields = None
    run_fields = None
    stage_acc = defaultdict(lambda: {"count": 0, **{c: 0.0 for c in RESOURCE_COLS}})
    run_rows = []
    failures = []
    event_count = 0

    with events_path.open("w", newline="", encoding="utf-8") as ef, runs_path.open("w", newline="", encoding="utf-8") as rf:
        ew = None
        rw = None
        for idx, row in enumerate(rows, 1):
            tmp = None
            try:
                tmp = download_to_temp(row)
                data = json.loads(tmp.read_text(errors="replace"))
                run, events = process_run(row, data)
                if ew is None:
                    event_fields = list(events[0].keys())
                    ew = csv.DictWriter(ef, fieldnames=event_fields)
                    ew.writeheader()
                if rw is None:
                    run_fields = list(run.keys())
                    rw = csv.DictWriter(rf, fieldnames=run_fields)
                    rw.writeheader()
                ew.writerows(events)
                rw.writerow(run)
                run_rows.append(run)
                for ev in events:
                    dst = stage_acc[ev["stage_id"]]
                    dst["count"] += 1
                    for col in RESOURCE_COLS:
                        dst[col] += float(ev[col])
                event_count += len(events)
                if idx % 25 == 0 or idx == len(rows):
                    print(f"processed {idx}/{len(rows)} runs events={event_count}", flush=True)
            except Exception as exc:
                failures.append({**row, "error": str(exc)[:500], "rel_path": rel_path(row)})
                print(f"FAILED {idx}/{len(rows)} {row['benchmark']} {row['task_id']} {exc}", flush=True)
            finally:
                if tmp is not None:
                    tmp.unlink(missing_ok=True)

    if failures:
        with fail_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(failures[0].keys()))
            w.writeheader()
            w.writerows(failures)

    summary_rows = []
    for stage_id in STAGES:
        acc = stage_acc[stage_id]
        count = acc["count"]
        out = {"source": "AgentRewardBench", "scope": suffix, "stage_id": stage_id, "stage_name": STAGES[stage_id], "event_count": count}
        for col in RESOURCE_COLS:
            out[col] = round(acc[col] / count, 3) if count else 0
        summary_rows.append(out)
    summary_path = OUT / f"arb_stage_resource_summary_{suffix}.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    bench_counter = Counter(r["benchmark"] for r in run_rows)
    success_counter = Counter((r["benchmark"], r["human_success_label"]) for r in run_rows)
    run_summary_path = OUT / f"arb_run_summary_{suffix}.csv"
    with run_summary_path.open("w", newline="", encoding="utf-8") as f:
        fields = ["benchmark", "runs", "successful", "unsuccessful", "avg_steps", "avg_input_tokens", "avg_output_tokens", "avg_error_steps"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for benchmark in sorted(bench_counter):
            subset = [r for r in run_rows if r["benchmark"] == benchmark]
            n = len(subset)
            def avg(name):
                vals = [float(r[name] or 0) for r in subset]
                return round(sum(vals) / n, 2) if n else 0
            w.writerow({
                "benchmark": benchmark,
                "runs": n,
                "successful": success_counter[(benchmark, "Successful")],
                "unsuccessful": success_counter[(benchmark, "Unsuccessful")],
                "avg_steps": avg("n_steps"),
                "avg_input_tokens": avg("cum_input_tokens"),
                "avg_output_tokens": avg("cum_output_tokens"),
                "avg_error_steps": avg("error_steps"),
            })

    heatmap_path = REP / f"arb_stage_resource_heatmap_{suffix}.svg"
    write_heatmap(summary_rows, heatmap_path, f"AgentRewardBench {suffix} stage-resource proxy heatmap")

    report = [
        f"# AgentRewardBench P0 Summary ({suffix})\n",
        f"- Target trajectories: {len(rows)}\n",
        f"- Processed trajectories: {len(run_rows)}\n",
        f"- Failed trajectories: {len(failures)}\n",
        f"- Events: {event_count}\n",
        f"- Events CSV: `{events_path}`\n",
        f"- Runs CSV: `{runs_path}`\n",
        f"- Stage summary: `{summary_path}`\n",
        f"- Heatmap: `{heatmap_path}`\n",
        "\n## Benchmark Counts\n",
    ]
    for benchmark, count in sorted(bench_counter.items()):
        report.append(f"- {benchmark}: {count}\n")
    report.append("\n## Interpretation\n")
    report.append("- This source represents web/GUI agent flows. Unlike tau-bench, browser/display and observation/context phases are first-class resource consumers.\n")
    report.append("- S2/S3 are observation and context-building phases driven by screenshots, accessibility trees, DOM-derived text, and browser state.\n")
    report.append("- S4 remains accelerator/HBM heavy due to per-step LLM/VLM decision making.\n")
    report.append("- S5/S6 capture browser actuation and page/environment wait, shifting demand toward CPU, network, and display/browser resources.\n")
    (REP / f"arb_p0_summary_{suffix}.md").write_text("".join(report), encoding="utf-8")

    print(f"processed_runs={len(run_rows)} failed={len(failures)} events={event_count}")
    print(f"wrote {events_path}")
    print(f"wrote {heatmap_path}")


if __name__ == "__main__":
    main()
