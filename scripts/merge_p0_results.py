import csv
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
    "S5": "actuation",
    "S6": "environment_result_wait",
    "S7": "feedback_error_recovery",
    "S8": "validation_finalization",
}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields=None):
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def combine_files(paths, dest):
    rows = []
    for path in paths:
        if path.exists():
            rows.extend(read_csv(path))
    write_csv(dest, rows)
    return rows


def aggregate_stage(rows, source, scope):
    acc = defaultdict(lambda: {"count": 0, **{c: 0.0 for c in RESOURCE_COLS}})
    for row in rows:
        stage = row["stage_id"]
        dst = acc[stage]
        dst["count"] += 1
        for col in RESOURCE_COLS:
            dst[col] += float(row.get(col) or 0)
    out = []
    for stage_id, stage_name in STAGES.items():
        data = acc[stage_id]
        count = data["count"]
        row = {
            "source": source,
            "scope": scope,
            "stage_id": stage_id,
            "stage_name": stage_name,
            "event_count": count,
        }
        for col in RESOURCE_COLS:
            row[col] = round(data[col] / count, 3) if count else 0
        out.append(row)
    return out


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


arb_events = combine_files([OUT / "arb_events_all.csv", OUT / "arb_events_retry.csv"], OUT / "arb_events_complete.csv")
arb_runs = combine_files([OUT / "arb_runs_all.csv", OUT / "arb_runs_retry.csv"], OUT / "arb_runs_complete.csv")
arb_stage = aggregate_stage(arb_events, "AgentRewardBench", "complete")
write_csv(OUT / "arb_stage_resource_summary_complete.csv", arb_stage)
write_heatmap(arb_stage, REP / "arb_stage_resource_heatmap_complete.svg", "AgentRewardBench complete stage-resource proxy heatmap")

bench = defaultdict(list)
for row in arb_runs:
    bench[row["benchmark"]].append(row)
run_summary = []
for name, rows in sorted(bench.items()):
    n = len(rows)
    success = sum(1 for r in rows if r["human_success_label"] == "Successful")

    def avg(key):
        vals = [float(r.get(key) or 0) for r in rows]
        return round(sum(vals) / n, 2) if n else 0

    run_summary.append({
        "benchmark": name,
        "runs": n,
        "successful": success,
        "unsuccessful": n - success,
        "avg_steps": avg("n_steps"),
        "avg_input_tokens": avg("cum_input_tokens"),
        "avg_output_tokens": avg("cum_output_tokens"),
        "avg_error_steps": avg("error_steps"),
    })
write_csv(OUT / "arb_run_summary_complete.csv", run_summary)

combined_stage = []
osworld_stage_path = OUT / "osworld_all_stage_resource_summary.csv"
osworld_runs_path = OUT / "osworld_all_runs.csv"
osworld_events_path = OUT / "osworld_all_events.csv"
osworld_label = "OSWorld-Verified all processed models"
if not osworld_stage_path.exists():
    osworld_stage_path = OUT / "osworld_autoglm_15steps_stage_resource_summary.csv"
    osworld_runs_path = OUT / "osworld_autoglm_15steps_runs.csv"
    osworld_events_path = OUT / "osworld_autoglm_15steps_events.csv"
    osworld_label = "OSWorld-Verified autoglm_15steps"

stage_paths = [
    OUT / "tau_stage_resource_summary.csv",
    OUT / "arb_stage_resource_summary_complete.csv",
    osworld_stage_path,
]
for path in stage_paths:
    if not path.exists():
        continue
    combined_stage.extend(read_csv(path))
write_csv(OUT / "p0_combined_stage_resource_summary.csv", combined_stage)

report = []
report.append("# P0 Agent Flow Hardware-Resource Summary\n\n")
report.append("## Sources Processed\n\n")
report.append(f"- tau-bench: {len(read_csv(OUT / 'tau_runs.csv'))} runs, {len(read_csv(OUT / 'tau_events.csv'))} events.\n")
report.append(f"- AgentRewardBench: {len(arb_runs)} runs, {len(arb_events)} events.\n")
if osworld_runs_path.exists() and osworld_events_path.exists():
    report.append(f"- {osworld_label}: {len(read_csv(osworld_runs_path))} runs, {len(read_csv(osworld_events_path))} events.\n")
report.append("\n## AgentRewardBench Complete Run Summary\n\n")
fields = ["benchmark", "runs", "successful", "unsuccessful", "avg_steps", "avg_input_tokens", "avg_output_tokens", "avg_error_steps"]
report.append("|" + "|".join(fields) + "|\n")
report.append("|" + "|".join(["---"] * len(fields)) + "|\n")
for row in run_summary:
    report.append("|" + "|".join(str(row[f]) for f in fields) + "|\n")
report.append("\n## Cross-Source Interpretation\n\n")
report.append("- tau-bench represents tool/API-heavy agent flow: S1/S4 are accelerator/HBM dominated, while S5/S6 shift to CPU/network/API service demand; browser/display demand is effectively absent.\n")
report.append("- AgentRewardBench represents web/GUI agent flow: S2/S3/S5/S6 introduce sustained browser/display, CPU, memory, and network demand around each LLM decision.\n")
report.append("- OSWorld-Verified represents desktop/GUI/VM agent flow: S0/S5/S6/S8 add strong VM/container, display, CPU, and storage demand around real app execution and validation.\n")
report.append("- Across both sources, the flow alternates between accelerator-bound reasoning and environment-bound execution; this supports stage-aware rather than whole-flow-static resource allocation.\n")
report.append("- S7 feedback/error recovery is a resource amplifier: it re-enters observe/context/decide/act loops and causes repeated accelerator plus environment demand.\n")
report.append("\n## Artifacts\n\n")
for path in [
    OUT / "tau_events.csv",
    OUT / "arb_events_complete.csv",
    OUT / "p0_combined_stage_resource_summary.csv",
    REP / "tau_stage_resource_heatmap.svg",
    REP / "arb_stage_resource_heatmap_complete.svg",
    osworld_stage_path,
]:
    report.append(f"- `{path}`\n")
(REP / "p0_agent_flow_resource_summary.md").write_text("".join(report), encoding="utf-8")

print("arb_runs", len(arb_runs))
print("arb_events", len(arb_events))
print("wrote", OUT / "p0_combined_stage_resource_summary.csv")
print("wrote", REP / "p0_agent_flow_resource_summary.md")
