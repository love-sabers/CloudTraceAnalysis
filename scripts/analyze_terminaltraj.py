#!/usr/bin/env python3
"""Convert TerminalTraj parquet messages into unified trace-native events."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


STAGE_NAMES = {
    "S0": "setup",
    "S1": "goal_interpretation_planning",
    "S2": "observation_capture",
    "S3": "context_building",
    "S4": "action_decision",
    "S5": "actuation_terminal",
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

EVENT_FIELDS = [
    "source",
    "scope",
    "run_id",
    "stage_id",
    "stage_name",
    "event_type",
    "step_index",
    "role",
] + METRIC_FIELDS

ERROR_RE = re.compile(
    r"\b(error|failed|failure|traceback|exception|no such file|not found|command not found|permission denied|segmentation fault|timeout)\b",
    re.IGNORECASE,
)


def byte_len(text: str | None) -> int:
    return len((text or "").encode("utf-8"))


def token_proxy(text: str | None) -> int:
    # Mechanical approximation used only when provider token accounting is absent.
    return max(0, round(byte_len(text) / 4))


def empty_metrics() -> dict[str, float]:
    return {field: 0.0 for field in METRIC_FIELDS}


def event_row(
    run_id: str,
    stage_id: str,
    event_type: str,
    step_index: int,
    role: str,
    **metrics: float,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source": "TerminalTraj",
        "scope": "terminal_agent",
        "run_id": run_id,
        "stage_id": stage_id,
        "stage_name": STAGE_NAMES[stage_id],
        "event_type": event_type,
        "step_index": step_index,
        "role": role,
    }
    vals = empty_metrics()
    vals.update(metrics)
    vals["llm_total_tokens"] = (
        vals["llm_input_tokens"] + vals["llm_output_tokens"] + vals["llm_response_tokens"]
    )
    row.update(vals)
    return row


def parse_assistant_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def command_bytes(commands: Any) -> tuple[int, int]:
    if not isinstance(commands, list):
        return 0, 0
    total = 0
    count = 0
    for cmd in commands:
        if not isinstance(cmd, dict):
            continue
        total += byte_len(str(cmd.get("keystrokes") or ""))
        count += 1
    return total, count


def rows_for_message(run_id: str, step_index: int, message: dict[str, Any]) -> list[dict[str, Any]]:
    role = str(message.get("role") or "")
    content = str(message.get("content") or "")
    rows: list[dict[str, Any]] = []
    size = byte_len(content)

    if role == "user":
        if step_index == 0:
            rows.append(
                event_row(
                    run_id,
                    "S0",
                    "terminal_task_setup",
                    step_index,
                    role,
                    runtime_log_bytes=size,
                    text_bytes=size,
                )
            )
        rows.append(
            event_row(
                run_id,
                "S2",
                "terminal_observation",
                step_index,
                role,
                context_bytes=size,
                text_bytes=size,
            )
        )
        rows.append(
            event_row(
                run_id,
                "S3",
                "terminal_context_building",
                step_index,
                role,
                context_bytes=size,
            )
        )
        if step_index > 0:
            rows.append(
                event_row(
                    run_id,
                    "S6",
                    "terminal_result_wait",
                    step_index,
                    role,
                    runtime_log_bytes=size,
                    text_bytes=size,
                )
            )
        if ERROR_RE.search(content):
            rows.append(
                event_row(
                    run_id,
                    "S7",
                    "terminal_error_recovery",
                    step_index,
                    role,
                    retry_count=1.0,
                    error_count=1.0,
                    text_bytes=size,
                )
            )
        return rows

    if role == "assistant":
        parsed = parse_assistant_json(content)
        analysis = str(parsed.get("analysis") or "")
        plan = str(parsed.get("plan") or "")
        planning_text = "\n".join(x for x in [analysis, plan] if x)
        commands = parsed.get("commands")
        cmd_bytes, cmd_count = command_bytes(commands)
        task_complete = bool(parsed.get("task_complete"))

        if planning_text:
            planning_bytes = byte_len(planning_text)
            rows.append(
                event_row(
                    run_id,
                    "S1",
                    "terminal_agent_plan",
                    step_index,
                    role,
                    llm_output_tokens=token_proxy(planning_text),
                    reasoning_bytes=planning_bytes,
                    text_bytes=planning_bytes,
                )
            )

        rows.append(
            event_row(
                run_id,
                "S4",
                "terminal_action_decision",
                step_index,
                role,
                llm_output_tokens=token_proxy(content),
                action_bytes=cmd_bytes,
                text_bytes=size,
                tool_call_count=float(cmd_count),
            )
        )

        if cmd_count:
            rows.append(
                event_row(
                    run_id,
                    "S5",
                    "terminal_command_actuation",
                    step_index,
                    role,
                    action_bytes=cmd_bytes,
                    tool_arg_bytes=cmd_bytes,
                    tool_call_count=float(cmd_count),
                )
            )

        if task_complete:
            rows.append(
                event_row(
                    run_id,
                    "S8",
                    "terminal_validation_finalization",
                    step_index,
                    role,
                    text_bytes=size,
                )
            )
        return rows

    return rows


def iter_messages(path: Path):
    pf = pq.ParquetFile(path)
    offset = 0
    for batch in pf.iter_batches(batch_size=256, columns=["messages"]):
        messages = batch.column("messages").to_pylist()
        for local_idx, msg_list in enumerate(messages):
            yield offset + local_idx, msg_list or []
        offset += len(messages)


def write_events(parquet_dir: Path, output: Path, limit: int | None) -> dict[str, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(parquet_dir.glob("*.parquet"))
    runs = 0
    events = 0
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        writer.writeheader()
        for shard_id, parquet_path in enumerate(files):
            for row_idx, messages in iter_messages(parquet_path):
                if limit is not None and runs >= limit:
                    return {"runs": runs, "events": events, "shards": len(files)}
                run_id = f"terminaltraj::{parquet_path.stem}::{row_idx}"
                for step_index, message in enumerate(messages):
                    for row in rows_for_message(run_id, step_index, message):
                        writer.writerow(row)
                        events += 1
                runs += 1
    return {"runs": runs, "events": events, "shards": len(files)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet-dir", default="raw/terminaltraj/data")
    parser.add_argument("--output", default="processed/terminaltraj_events.csv")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    stats = write_events(Path(args.parquet_dir), Path(args.output), args.limit)
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
