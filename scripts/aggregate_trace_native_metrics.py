#!/usr/bin/env python3
"""Aggregate trace-native measured quantities from downloaded agent traces.

This script intentionally does not emit hand-labeled 0/1/2/3 resource levels.
It only uses quantities recorded in traces or derived mechanically from trace
fields: tokens, bytes, screenshots, tool calls, retries/errors, and elapsed
time when the trace provides it.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


STAGE_NAMES = {
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

METRIC_FIELDS = [
    "llm_input_tokens",
    "llm_output_tokens",
    "llm_response_tokens",
    "llm_total_tokens",
    "context_bytes",
    "text_bytes",
    "reasoning_bytes",
    "action_bytes",
    "tool_arg_bytes",
    "screenshot_bytes",
    "runtime_log_bytes",
    "tool_call_count",
    "retry_count",
    "error_count",
    "elapsed_sec",
]

RUN_STAGE_FIELDS = [
    "source",
    "scope",
    "run_id",
    "stage_id",
    "stage_name",
    "event_count",
    "elapsed_observed_events",
] + METRIC_FIELDS

SUMMARY_FIELDS = [
    "source",
    "scope",
    "stage_id",
    "stage_name",
    "run_stage_count",
    "run_count",
    "event_count",
    "elapsed_coverage_ratio",
]

for metric in METRIC_FIELDS:
    SUMMARY_FIELDS.extend(
        [
            f"{metric}_sum",
            f"{metric}_mean_per_run_stage",
            f"{metric}_p50_per_run_stage",
            f"{metric}_p95_per_run_stage",
            f"{metric}_max_per_run_stage",
        ]
    )


def fnum(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def inum(value) -> int:
    return int(fnum(value))


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def has_positive(row: dict[str, str], *names: str) -> bool:
    return any(fnum(row.get(name)) > 0 for name in names)


def normalize_source(row: dict[str, str], default_source: str) -> str:
    return row.get("source") or default_source


def normalize_scope(row: dict[str, str], source: str, fallback: str) -> str:
    if source == "AgentRewardBench":
        return row.get("benchmark") or fallback
    if source == "OSWorld-Verified":
        return row.get("model") or fallback
    if source == "tau-bench":
        model = row.get("model") or ""
        domain = row.get("domain") or ""
        return "::".join(x for x in [model, domain] if x) or fallback
    return fallback


def empty_metrics() -> dict[str, float]:
    return {name: 0.0 for name in METRIC_FIELDS}


def normalize_event(row: dict[str, str], default_source: str, fallback_scope: str) -> tuple[str, str, str, str, str, dict[str, float], int]:
    source = normalize_source(row, default_source)
    scope = normalize_scope(row, source, fallback_scope)
    run_id = row.get("run_id") or ""
    stage_id = row.get("stage_id") or "UNKNOWN"
    stage_name = row.get("stage_name") or STAGE_NAMES.get(stage_id, stage_id)
    event_type = row.get("event_type") or ""
    metrics = empty_metrics()
    elapsed_observed = 0

    if source == "AgentRewardBench":
        input_tokens = fnum(row.get("input_tokens"))
        output_tokens = fnum(row.get("output_tokens"))
        axtree_bytes = fnum(row.get("axtree_bytes"))
        reasoning_bytes = fnum(row.get("reasoning_bytes"))
        action_bytes = fnum(row.get("action_bytes"))
        err_bytes = fnum(row.get("last_action_error_bytes"))
        step_elapsed = fnum(row.get("step_elapsed")) or fnum(row.get("agent_elapsed"))

        if stage_id == "S1":
            metrics["llm_input_tokens"] = input_tokens
            metrics["reasoning_bytes"] = reasoning_bytes
            metrics["text_bytes"] = reasoning_bytes
        elif stage_id == "S2":
            metrics["context_bytes"] = axtree_bytes
            metrics["screenshot_bytes"] = 1.0 if inum(row.get("screenshot_present")) else 0.0
        elif stage_id == "S3":
            metrics["llm_input_tokens"] = input_tokens
            metrics["context_bytes"] = axtree_bytes
        elif stage_id == "S4":
            metrics["llm_input_tokens"] = input_tokens
            metrics["llm_output_tokens"] = output_tokens
            metrics["reasoning_bytes"] = reasoning_bytes
            metrics["action_bytes"] = action_bytes
            metrics["text_bytes"] = reasoning_bytes + action_bytes
        elif stage_id == "S5":
            metrics["action_bytes"] = action_bytes
        elif stage_id in {"S6", "S7"}:
            if step_elapsed > 0:
                metrics["elapsed_sec"] = step_elapsed
                elapsed_observed = 1
            metrics["retry_count"] = fnum(row.get("n_retry")) + fnum(row.get("n_retry_llm")) + fnum(row.get("busted_retry"))
            metrics["error_count"] = 1.0 if err_bytes > 0 or inum(row.get("error_proxy")) else 0.0
            metrics["text_bytes"] = err_bytes
        elif stage_id == "S8":
            metrics["text_bytes"] = err_bytes

    elif source == "OSWorld-Verified":
        response_tokens = fnum(row.get("response_tokens_proxy"))
        response_bytes = fnum(row.get("response_bytes"))
        action_bytes = fnum(row.get("action_bytes"))
        screenshot_bytes = fnum(row.get("screenshot_bytes"))
        log_bytes = fnum(row.get("runtime_log_bytes"))
        error = fnum(row.get("error_proxy"))

        if stage_id == "S0":
            metrics["runtime_log_bytes"] = log_bytes
        elif stage_id == "S1":
            metrics["llm_response_tokens"] = response_tokens
            metrics["llm_output_tokens"] = response_tokens
            metrics["text_bytes"] = response_bytes
            metrics["runtime_log_bytes"] = log_bytes
        elif stage_id == "S2":
            metrics["screenshot_bytes"] = screenshot_bytes
        elif stage_id == "S3":
            metrics["context_bytes"] = screenshot_bytes
        elif stage_id == "S4":
            metrics["llm_response_tokens"] = response_tokens
            metrics["llm_output_tokens"] = response_tokens
            metrics["text_bytes"] = response_bytes
            metrics["action_bytes"] = action_bytes
        elif stage_id == "S5":
            metrics["action_bytes"] = action_bytes
        elif stage_id == "S7":
            metrics["error_count"] = error
            metrics["text_bytes"] = response_bytes + action_bytes
        elif stage_id == "S8":
            metrics["runtime_log_bytes"] = log_bytes

    elif source == "tau-bench":
        input_tokens = fnum(row.get("input_tokens_proxy"))
        output_tokens = fnum(row.get("output_tokens_proxy"))
        content_bytes = fnum(row.get("content_bytes"))
        tool_arg_bytes = fnum(row.get("tool_arg_bytes"))
        tool_calls = fnum(row.get("tool_call_count"))
        retry = fnum(row.get("retry_or_error_proxy"))
        if stage_id in {"S1", "S2", "S3"}:
            metrics["llm_input_tokens"] = input_tokens
            metrics["context_bytes"] = content_bytes + tool_arg_bytes
            metrics["text_bytes"] = content_bytes
        elif stage_id == "S4":
            metrics["llm_output_tokens"] = output_tokens
            metrics["llm_input_tokens"] = input_tokens
            metrics["text_bytes"] = content_bytes
            metrics["tool_call_count"] = tool_calls
        elif stage_id == "S5":
            metrics["tool_arg_bytes"] = tool_arg_bytes
            metrics["tool_call_count"] = max(tool_calls, 1.0 if tool_arg_bytes > 0 else 0.0)
        elif stage_id == "S6":
            metrics["text_bytes"] = content_bytes
            metrics["context_bytes"] = content_bytes
        elif stage_id == "S7":
            metrics["error_count"] = retry
            metrics["text_bytes"] = content_bytes
        elif stage_id == "S8":
            metrics["text_bytes"] = content_bytes

    else:
        for field in METRIC_FIELDS:
            metrics[field] = fnum(row.get(field))

    metrics["llm_total_tokens"] = metrics["llm_input_tokens"] + metrics["llm_output_tokens"] + metrics["llm_response_tokens"]
    if has_positive(row, "step_elapsed", "agent_elapsed"):
        elapsed_observed = max(elapsed_observed, 1)
    return source, scope, run_id, stage_id, stage_name, metrics, elapsed_observed


def select_event_files(processed: Path) -> list[tuple[Path, str, str]]:
    files: list[tuple[Path, str, str]] = []
    tau = processed / "tau_events.csv"
    if tau.exists():
        files.append((tau, "tau-bench", "all"))

    for name in ["arb_events_complete.csv", "arb_events_all.csv", "arb_events_sample.csv"]:
        path = processed / name
        if path.exists():
            files.append((path, "AgentRewardBench", name.replace("arb_events_", "").replace(".csv", "")))
            break

    os_all = processed / "osworld_all_events.csv"
    if os_all.exists():
        files.append((os_all, "OSWorld-Verified", "all_models"))
    else:
        for path in sorted(processed.glob("osworld_*_events.csv")):
            if path.name == "osworld_all_events.csv":
                continue
            model = path.name[len("osworld_") : -len("_events.csv")]
            files.append((path, "OSWorld-Verified", model))
    return files


def update_run_stage(dst: dict[str, object], metrics: dict[str, float], elapsed_observed: int) -> None:
    dst["event_count"] = int(dst["event_count"]) + 1
    dst["elapsed_observed_events"] = int(dst["elapsed_observed_events"]) + elapsed_observed
    for field in METRIC_FIELDS:
        dst[field] = float(dst[field]) + metrics[field]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(run_stage_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in run_stage_rows:
        key = (str(row["source"]), str(row["scope"]), str(row["stage_id"]), str(row["stage_name"]))
        groups[key].append(row)

    out = []
    for (source, scope, stage_id, stage_name), rows in sorted(groups.items()):
        event_count = sum(inum(r["event_count"]) for r in rows)
        elapsed_observed = sum(inum(r["elapsed_observed_events"]) for r in rows)
        summary: dict[str, object] = {
            "source": source,
            "scope": scope,
            "stage_id": stage_id,
            "stage_name": stage_name,
            "run_stage_count": len(rows),
            "run_count": len({r["run_id"] for r in rows}),
            "event_count": event_count,
            "elapsed_coverage_ratio": round(elapsed_observed / event_count, 6) if event_count else 0.0,
        }
        for metric in METRIC_FIELDS:
            values = [float(r[metric]) for r in rows]
            total = sum(values)
            summary[f"{metric}_sum"] = round(total, 6)
            summary[f"{metric}_mean_per_run_stage"] = round(total / len(values), 6) if values else 0.0
            summary[f"{metric}_p50_per_run_stage"] = round(percentile(values, 0.50), 6)
            summary[f"{metric}_p95_per_run_stage"] = round(percentile(values, 0.95), 6)
            summary[f"{metric}_max_per_run_stage"] = round(max(values), 6) if values else 0.0
        out.append(summary)
    return out


def write_report(path: Path, run_stage_rows: list[dict[str, object]], summary_rows: list[dict[str, object]], files: list[tuple[Path, str, str]]) -> None:
    lines = ["# Trace-Native Measured Resource Metrics\n\n"]
    lines.append("This report uses only quantities present in downloaded traces or mechanical byte/token counts derived from trace fields. It does not use proxy 0/1/2/3 resource levels.\n\n")
    lines.append("## Inputs\n\n")
    for file_path, source, scope in files:
        lines.append(f"- {source} / {scope}: `{file_path}`\n")
    lines.append("\n## Output Tables\n\n")
    lines.append("- `processed/trace_native_run_stage_metrics.csv`: run-stage measured quantities.\n")
    lines.append("- `processed/trace_native_stage_summary.csv`: source/scope/stage aggregate sums, p50, p95, max.\n")
    lines.append("- `processed/trace_native_metric_coverage.csv`: which sources contain real elapsed-time fields.\n\n")
    lines.append("## Coverage\n\n")
    coverage = defaultdict(lambda: {"events": 0, "elapsed_events": 0, "run_stages": 0})
    for row in run_stage_rows:
        key = (row["source"], row["scope"])
        coverage[key]["events"] += inum(row["event_count"])
        coverage[key]["elapsed_events"] += inum(row["elapsed_observed_events"])
        coverage[key]["run_stages"] += 1
    lines.append("|source|scope|run_stages|events|elapsed_coverage_ratio|\n")
    lines.append("|---|---|---:|---:|---:|\n")
    for (source, scope), data in sorted(coverage.items()):
        ratio = data["elapsed_events"] / data["events"] if data["events"] else 0.0
        lines.append(f"|{source}|{scope}|{data['run_stages']}|{data['events']}|{ratio:.6f}|\n")
    lines.append("\n## Notes\n\n")
    lines.append("- `elapsed_sec` is emitted only when traces include elapsed fields. Missing time is left as zero with low coverage rather than estimated.\n")
    lines.append("- `screenshot_bytes` is real byte size for OSWorld screenshots. AgentRewardBench currently exposes screenshot presence in processed events, not screenshot file bytes.\n")
    lines.append("- Stage assignment is semantic, but each metric value is trace-native: token counts, byte counts, elapsed values, retry/error counts, and tool-call counts.\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="/root/liujun/saber/project/CloudTrace")
    args = parser.parse_args()
    root = Path(args.root)
    processed = root / "processed"
    reports = root / "reports"
    files = select_event_files(processed)
    if not files:
        raise SystemExit(f"No event files found in {processed}")

    run_stage: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    for file_path, default_source, fallback_scope in files:
        with file_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                source, scope, run_id, stage_id, stage_name, metrics, elapsed_observed = normalize_event(row, default_source, fallback_scope)
                key = (source, scope, run_id, stage_id, stage_name)
                if key not in run_stage:
                    run_stage[key] = {
                        "source": source,
                        "scope": scope,
                        "run_id": run_id,
                        "stage_id": stage_id,
                        "stage_name": stage_name,
                        "event_count": 0,
                        "elapsed_observed_events": 0,
                        **empty_metrics(),
                    }
                update_run_stage(run_stage[key], metrics, elapsed_observed)

    run_stage_rows = sorted(run_stage.values(), key=lambda r: (str(r["source"]), str(r["scope"]), str(r["run_id"]), str(r["stage_id"])))
    summary_rows = build_summary(run_stage_rows)
    write_csv(processed / "trace_native_run_stage_metrics.csv", run_stage_rows, RUN_STAGE_FIELDS)
    write_csv(processed / "trace_native_stage_summary.csv", summary_rows, SUMMARY_FIELDS)

    coverage_rows = []
    for row in summary_rows:
        coverage_rows.append(
            {
                "source": row["source"],
                "scope": row["scope"],
                "stage_id": row["stage_id"],
                "stage_name": row["stage_name"],
                "event_count": row["event_count"],
                "elapsed_coverage_ratio": row["elapsed_coverage_ratio"],
            }
        )
    write_csv(processed / "trace_native_metric_coverage.csv", coverage_rows, ["source", "scope", "stage_id", "stage_name", "event_count", "elapsed_coverage_ratio"])
    write_report(reports / "trace_native_measured_summary.md", run_stage_rows, summary_rows, files)
    print(json.dumps({
        "event_files": [str(path) for path, _, _ in files],
        "run_stage_rows": len(run_stage_rows),
        "summary_rows": len(summary_rows),
        "outputs": [
            str(processed / "trace_native_run_stage_metrics.csv"),
            str(processed / "trace_native_stage_summary.csv"),
            str(processed / "trace_native_metric_coverage.csv"),
            str(reports / "trace_native_measured_summary.md"),
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
