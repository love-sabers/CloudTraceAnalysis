import csv
from collections import defaultdict
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


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def write_csv(path, rows, fields=None):
    rows = list(rows)
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def model_from(path, suffix):
    name = path.name
    return name[len("osworld_") : -len(suffix)]


def event_files():
    for path in sorted(OUT.glob("osworld_*_events.csv")):
        if path.name.startswith("osworld_all_"):
            continue
        yield path


def run_files():
    for path in sorted(OUT.glob("osworld_*_runs.csv")):
        if path.name.startswith("osworld_all_"):
            continue
        yield path


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

    by_stage = {row["stage_id"]: row for row in summary_rows}
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    svg.append('<rect width="100%" height="100%" fill="white"/>')
    svg.append(f'<text x="20" y="30" font-family="Arial" font-size="20" font-weight="700">{esc(title)}</text>')
    svg.append('<text x="20" y="52" font-family="Arial" font-size="12" fill="#555">0=none, 1=low, 2=medium, 3=high; proxy demand from trace events, not direct counters</text>')
    for j, col in enumerate(RESOURCE_COLS):
        x = left + j * cell_w + cell_w / 2
        svg.append(f'<text x="{x}" y="{top - 12}" font-family="Arial" font-size="11" text-anchor="middle">{esc(col.replace("_", " "))}</text>')
    for i, stage_id in enumerate(STAGES):
        row = by_stage.get(stage_id, {"stage_name": STAGES[stage_id], **{c: 0 for c in RESOURCE_COLS}})
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
    stage_acc = defaultdict(lambda: {"count": 0, **{col: 0.0 for col in RESOURCE_COLS}})
    model_events = defaultdict(int)
    model_stage_events = defaultdict(lambda: defaultdict(int))
    all_events_path = OUT / "osworld_all_events.csv"
    event_fields = None

    with all_events_path.open("w", newline="", encoding="utf-8") as out_f:
        writer = None
        for path in event_files():
            model = model_from(path, "_events.csv")
            for row in read_csv(path):
                if writer is None:
                    event_fields = list(row.keys())
                    writer = csv.DictWriter(out_f, fieldnames=event_fields)
                    writer.writeheader()
                writer.writerow(row)
                stage_id = row["stage_id"]
                dst = stage_acc[stage_id]
                dst["count"] += 1
                model_events[model] += 1
                model_stage_events[model][stage_id] += 1
                for col in RESOURCE_COLS:
                    dst[col] += float(row.get(col) or 0)

    stage_rows = []
    for stage_id, stage_name in STAGES.items():
        data = stage_acc[stage_id]
        count = data["count"]
        row = {
            "source": "OSWorld-Verified",
            "scope": "all_models",
            "stage_id": stage_id,
            "stage_name": stage_name,
            "event_count": count,
        }
        for col in RESOURCE_COLS:
            row[col] = round(data[col] / count, 3) if count else 0
        stage_rows.append(row)
    write_csv(OUT / "osworld_all_stage_resource_summary.csv", stage_rows)
    write_heatmap(stage_rows, REP / "osworld_all_stage_resource_heatmap.svg", "OSWorld all models stage-resource proxy heatmap")

    all_runs_path = OUT / "osworld_all_runs.csv"
    run_fields = None
    model_runs = defaultdict(lambda: {"runs": 0, "successes": 0, "steps": 0.0, "events": 0})
    domain_runs = defaultdict(lambda: {"runs": 0, "successes": 0, "steps": 0.0})
    with all_runs_path.open("w", newline="", encoding="utf-8") as out_f:
        writer = None
        for path in run_files():
            model = model_from(path, "_runs.csv")
            for row in read_csv(path):
                if writer is None:
                    run_fields = list(row.keys())
                    writer = csv.DictWriter(out_f, fieldnames=run_fields)
                    writer.writeheader()
                writer.writerow(row)
                success = int(float(row.get("success") or 0))
                steps = float(row.get("steps") or row.get("n_steps") or 0)
                domain = row.get("domain") or "unknown"
                model_runs[model]["runs"] += 1
                model_runs[model]["successes"] += success
                model_runs[model]["steps"] += steps
                domain_runs[domain]["runs"] += 1
                domain_runs[domain]["successes"] += success
                domain_runs[domain]["steps"] += steps

    model_rows = []
    for model, stats in sorted(model_runs.items()):
        runs = stats["runs"]
        model_rows.append(
            {
                "model": model,
                "runs": runs,
                "events": model_events.get(model, 0),
                "successes": stats["successes"],
                "success_rate": round(stats["successes"] / runs, 3) if runs else 0,
                "avg_steps": round(stats["steps"] / runs, 2) if runs else 0,
            }
        )
    write_csv(OUT / "osworld_all_model_summary.csv", model_rows)

    domain_rows = []
    for domain, stats in sorted(domain_runs.items()):
        runs = stats["runs"]
        domain_rows.append(
            {
                "domain": domain,
                "runs": runs,
                "successes": stats["successes"],
                "success_rate": round(stats["successes"] / runs, 3) if runs else 0,
                "avg_steps": round(stats["steps"] / runs, 2) if runs else 0,
            }
        )
    write_csv(OUT / "osworld_all_domain_summary.csv", domain_rows)

    report = ["# OSWorld-Verified P0 Summary (All Processed Models)\n\n"]
    report.append(f"- Models processed: {len(model_rows)}\n")
    report.append(f"- Runs: {sum(row['runs'] for row in model_rows)}\n")
    report.append(f"- Events: {sum(row['events'] for row in model_rows)}\n")
    total_runs = sum(row["runs"] for row in model_rows)
    total_success = sum(row["successes"] for row in model_rows)
    report.append(f"- Success rate: {total_success / total_runs:.3f}\n" if total_runs else "- Success rate: n/a\n")
    report.append("\n## Model Summary\n\n")
    fields = ["model", "runs", "events", "successes", "success_rate", "avg_steps"]
    report.append("|" + "|".join(fields) + "|\n")
    report.append("|" + "|".join(["---"] * len(fields)) + "|\n")
    for row in model_rows:
        report.append("|" + "|".join(str(row[field]) for field in fields) + "|\n")
    report.append("\n## Domain Summary\n\n")
    fields = ["domain", "runs", "successes", "success_rate", "avg_steps"]
    report.append("|" + "|".join(fields) + "|\n")
    report.append("|" + "|".join(["---"] * len(fields)) + "|\n")
    for row in domain_rows:
        report.append("|" + "|".join(str(row[field]) for field in fields) + "|\n")
    report.append("\n## Resource Interpretation\n\n")
    report.append("- S0/S5/S6/S8 are consistently environment-bound: VM/container isolation, display/graphics, CPU, and storage demand are high because OSWorld exercises real desktop apps and validation.\n")
    report.append("- S1/S3/S4 are reasoning/context-bound: accelerator and HBM demand stay high around prompt construction and action synthesis.\n")
    report.append("- OSWorld therefore exposes heterogeneous demand inside one flow: model-serving phases alternate with desktop-environment phases, and S7 loops amplify both sides when recovery is needed.\n")
    report.append("\n## Artifacts\n\n")
    for path in [
        OUT / "osworld_all_events.csv",
        OUT / "osworld_all_runs.csv",
        OUT / "osworld_all_stage_resource_summary.csv",
        OUT / "osworld_all_model_summary.csv",
        OUT / "osworld_all_domain_summary.csv",
        REP / "osworld_all_stage_resource_heatmap.svg",
    ]:
        report.append(f"- `{path}`\n")
    (REP / "osworld_all_p0_summary.md").write_text("".join(report), encoding="utf-8")

    print("models", len(model_rows))
    print("runs", total_runs)
    print("events", sum(row["events"] for row in model_rows))
    print("wrote", OUT / "osworld_all_stage_resource_summary.csv")
    print("wrote", REP / "osworld_all_p0_summary.md")


if __name__ == "__main__":
    main()
