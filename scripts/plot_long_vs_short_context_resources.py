#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis_outputs" / "decode_weight_kv_theory"

BYTES_PER_GB = 1_000_000_000
FLOPS_PER_TFLOPS = 1_000_000_000_000


@dataclass(frozen=True)
class Model:
    name: str
    active_params_b: float
    layers: int
    hidden_size: int
    kv_bytes_per_token_bf16: int


@dataclass(frozen=True)
class Hardware:
    name: str
    tp_size: int
    compute_tflops_per_gpu: float
    bandwidth_gb_s_per_gpu: float


@dataclass(frozen=True)
class Scenario:
    name: str
    input_tokens_by_turn: list[int]
    output_tokens_by_turn: list[int]


MODEL = Model(
    name="Qwen3-Coder-480B-A35B",
    active_params_b=35.0,
    layers=62,
    hidden_size=6144,
    kv_bytes_per_token_bf16=253_952,
)

HARDWARE = Hardware(
    name="A800-class TP8 theoretical per-GPU",
    tp_size=8,
    compute_tflops_per_gpu=312.0,
    bandwidth_gb_s_per_gpu=900.0,
)

SCENARIOS = [
    Scenario(
        name="multi_turn_ultra_long",
        input_tokens_by_turn=[128_000, 64_000, 64_000, 64_000, 64_000],
        output_tokens_by_turn=[2_048, 2_048, 2_048, 2_048, 2_048],
    ),
    Scenario(
        name="few_turn_lower_accumulated_context",
        input_tokens_by_turn=[128_000, 64_000],
        output_tokens_by_turn=[2_048, 2_048],
    ),
]

PREFILL_CHUNK_TOKENS = 2048
DECODE_CHUNK_TOKENS = 128


def per_gpu_active_weight_bytes(model: Model, hw: Hardware) -> float:
    return model.active_params_b * 1e9 * 2 / hw.tp_size


def per_gpu_kv_bytes_per_token(model: Model, hw: Hardware) -> float:
    return model.kv_bytes_per_token_bf16 / hw.tp_size


def prefill_chunk_cost(model: Model, hw: Hardware, context_before: int, new_tokens: int) -> tuple[float, float, float]:
    linear_flops = 2 * model.active_params_b * 1e9 * new_tokens / hw.tp_size
    attention_pairs = context_before * new_tokens + new_tokens * (new_tokens + 1) / 2
    attention_flops = 4 * model.layers * model.hidden_size * attention_pairs / hw.tp_size
    flops = linear_flops + attention_flops

    weight_read = per_gpu_active_weight_bytes(model, hw)
    kv_read = per_gpu_kv_bytes_per_token(model, hw) * context_before
    kv_write = per_gpu_kv_bytes_per_token(model, hw) * new_tokens
    kv_bytes = kv_read + kv_write
    bytes_moved = weight_read + kv_bytes
    return flops, bytes_moved, kv_bytes


def decode_chunk_cost(model: Model, hw: Hardware, context_before: int, new_tokens: int) -> tuple[float, float, float]:
    flops = 0.0
    bytes_moved = 0.0
    kv_bytes = 0.0
    weight_read_per_token = per_gpu_active_weight_bytes(model, hw)
    kv_per_token = per_gpu_kv_bytes_per_token(model, hw)
    for i in range(new_tokens):
        ctx = context_before + i
        linear_flops = 2 * model.active_params_b * 1e9 / hw.tp_size
        attention_flops = 4 * model.layers * model.hidden_size * ctx / hw.tp_size
        flops += linear_flops + attention_flops
        token_kv_bytes = kv_per_token * ctx + kv_per_token
        kv_bytes += token_kv_bytes
        bytes_moved += weight_read_per_token + token_kv_bytes
    return flops, bytes_moved, kv_bytes


def duration_seconds(flops: float, bytes_moved: float, hw: Hardware) -> float:
    compute_time = flops / (hw.compute_tflops_per_gpu * FLOPS_PER_TFLOPS)
    memory_time = bytes_moved / (hw.bandwidth_gb_s_per_gpu * BYTES_PER_GB)
    return max(compute_time, memory_time, 1e-9)


def append_segment(
    rows: list[dict],
    scenario: str,
    turn: int,
    phase: str,
    start_time: float,
    duration: float,
    context_start: int,
    context_end: int,
    flops: float,
    bytes_moved: float,
    kv_bytes: float,
    chunk_tokens: int,
) -> None:
    achieved_tflops = flops / duration / FLOPS_PER_TFLOPS
    achieved_bandwidth = bytes_moved / duration / BYTES_PER_GB
    achieved_kv_bandwidth = kv_bytes / duration / BYTES_PER_GB
    rows.append(
        {
            "scenario": scenario,
            "turn": turn,
            "phase": phase,
            "start_time_s": start_time,
            "end_time_s": start_time + duration,
            "time_s": start_time,
            "context_start_tokens": context_start,
            "context_end_tokens": context_end,
            "context_tokens": context_end,
            "resident_kv_start_gb_per_gpu": context_start * per_gpu_kv_bytes_per_token(MODEL, HARDWARE) / BYTES_PER_GB,
            "resident_kv_end_gb_per_gpu": context_end * per_gpu_kv_bytes_per_token(MODEL, HARDWARE) / BYTES_PER_GB,
            "resident_kv_gb_per_gpu": context_end * per_gpu_kv_bytes_per_token(MODEL, HARDWARE) / BYTES_PER_GB,
            "compute_tflops_per_gpu": achieved_tflops,
            "compute_work_tflop_per_gpu": flops / FLOPS_PER_TFLOPS,
            "memory_bandwidth_gb_s_per_gpu": achieved_bandwidth,
            "kv_memory_bandwidth_gb_s_per_gpu": achieved_kv_bandwidth,
            "phase_duration_s": duration,
            "chunk_tokens": chunk_tokens,
            "chunk_flops_per_gpu": flops,
            "chunk_bytes_per_gpu": bytes_moved,
            "chunk_kv_bytes_per_gpu": kv_bytes,
        }
    )


def simulate_scenario(scenario: Scenario) -> pd.DataFrame:
    rows: list[dict] = []
    time_s = 0.0
    context = 0
    for turn_idx, (input_tokens, output_tokens) in enumerate(
        zip(scenario.input_tokens_by_turn, scenario.output_tokens_by_turn),
        start=1,
    ):
        remaining = input_tokens
        while remaining > 0:
            chunk = min(PREFILL_CHUNK_TOKENS, remaining)
            flops, bytes_moved, kv_bytes = prefill_chunk_cost(MODEL, HARDWARE, context, chunk)
            dur = duration_seconds(flops, bytes_moved, HARDWARE)
            append_segment(
                rows,
                scenario.name,
                turn_idx,
                "prefill",
                time_s,
                dur,
                context,
                context + chunk,
                flops,
                bytes_moved,
                kv_bytes,
                chunk,
            )
            time_s += dur
            context += chunk
            remaining -= chunk

        remaining = output_tokens
        while remaining > 0:
            chunk = min(DECODE_CHUNK_TOKENS, remaining)
            flops, bytes_moved, kv_bytes = decode_chunk_cost(MODEL, HARDWARE, context, chunk)
            dur = duration_seconds(flops, bytes_moved, HARDWARE)
            append_segment(
                rows,
                scenario.name,
                turn_idx,
                "decode",
                time_s,
                dur,
                context,
                context + chunk,
                flops,
                bytes_moved,
                kv_bytes,
                chunk,
            )
            time_s += dur
            context += chunk
            remaining -= chunk
    return pd.DataFrame(rows)


def write_assumptions() -> None:
    rows = [
        {
            "model": MODEL.name,
            "active_params_b": MODEL.active_params_b,
            "layers": MODEL.layers,
            "hidden_size": MODEL.hidden_size,
            "kv_bytes_per_token_bf16_global": MODEL.kv_bytes_per_token_bf16,
            "hardware": HARDWARE.name,
            "tp_size": HARDWARE.tp_size,
            "compute_tflops_per_gpu": HARDWARE.compute_tflops_per_gpu,
            "bandwidth_gb_s_per_gpu": HARDWARE.bandwidth_gb_s_per_gpu,
            "prefill_chunk_tokens": PREFILL_CHUNK_TOKENS,
            "decode_chunk_tokens": DECODE_CHUNK_TOKENS,
            "prefill_flops": "2*active_params*new_tokens/TP + 4*layers*hidden*(past*new + new^2/2)/TP",
            "decode_flops": "sum over generated tokens: 2*active_params/TP + 4*layers*hidden*context/TP",
            "prefill_bytes": "active_weight_bytes/TP + past_KV_bytes/TP + new_KV_write_bytes/TP; KV-only bandwidth excludes active weights",
            "decode_bytes": "per token active_weight_bytes/TP + context_KV_read_bytes/TP + KV_write_bytes/TP; KV-only bandwidth excludes active weights",
            "duration": "max(compute_time, memory_time) per chunk",
            "scenario_note": "Both scenarios use long per-turn inputs; the short-context case is short because it has fewer accumulated turns, not because each prompt is tiny.",
        }
    ]
    out = OUT_DIR / "long_vs_short_context_resource_assumptions.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(out)


def build_curves() -> pd.DataFrame:
    frames = [simulate_scenario(s) for s in SCENARIOS]
    df = pd.concat(frames, ignore_index=True)
    out = OUT_DIR / "long_vs_short_context_resource_curves.csv"
    df.to_csv(out, index=False)
    print(out)
    return df


def phase_spans(df: pd.DataFrame) -> pd.DataFrame:
    spans = (
        df.groupby(["scenario", "turn", "phase"], as_index=False)
        .agg(start=("start_time_s", "min"), end=("end_time_s", "max"))
        .sort_values(["scenario", "start"])
    )
    return spans


def step_series(part: pd.DataFrame, metric: str) -> tuple[np.ndarray, np.ndarray]:
    x: list[float] = []
    y: list[float] = []
    for _, row in part.iterrows():
        x.extend([row["start_time_s"] / 60.0, row["end_time_s"] / 60.0])
        y.extend([row[metric], row[metric]])
    return np.array(x), np.array(y)


def capacity_series(part: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    x: list[float] = []
    y: list[float] = []
    for _, row in part.iterrows():
        x.extend([row["start_time_s"] / 60.0, row["end_time_s"] / 60.0])
        y.extend([row["resident_kv_start_gb_per_gpu"], row["resident_kv_end_gb_per_gpu"]])
    return np.array(x), np.array(y)


def plot_curves(df: pd.DataFrame) -> None:
    scenario_names = [s.name for s in SCENARIOS]
    metrics = [
        ("compute_work_tflop_per_gpu", "Compute work per chunk per GPU (TFLOP)"),
        ("resident_kv_gb_per_gpu", "Resident KV capacity per GPU (GB)"),
        ("memory_bandwidth_gb_s_per_gpu", "Memory bandwidth per GPU (GB/s)"),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(14.5, 9.2), sharex=True)
    spans = phase_spans(df)
    colors = {"prefill": "#dbeafe", "decode": "#fef3c7"}

    for col, scenario in enumerate(scenario_names):
        part = df[df["scenario"] == scenario].sort_values("time_s")
        for row, (metric, ylabel) in enumerate(metrics):
            ax = axes[row, col]
            for _, span in spans[spans["scenario"] == scenario].iterrows():
                ax.axvspan(
                    span["start"] / 60.0,
                    span["end"] / 60.0,
                    color=colors[span["phase"]],
                    alpha=0.42,
                    linewidth=0,
                )
            if metric == "resident_kv_gb_per_gpu":
                x_cap, y_cap = capacity_series(part)
                ax.plot(x_cap, y_cap, color="#111827", linewidth=1.8)
            elif metric == "memory_bandwidth_gb_s_per_gpu":
                x_total, y_total = step_series(part, "memory_bandwidth_gb_s_per_gpu")
                x_kv, y_kv = step_series(part, "kv_memory_bandwidth_gb_s_per_gpu")
                ax.plot(
                    x_total,
                    y_total,
                    color="#111827",
                    linewidth=1.8,
                    label="total",
                )
                ax.plot(
                    x_kv,
                    y_kv,
                    color="#2563eb",
                    linewidth=1.5,
                    linestyle="--",
                    label="KV only",
                )
                if col == 1:
                    ax.legend(frameon=False, fontsize=8, loc="lower right")
            else:
                x_step, y_step = step_series(part, metric)
                ax.plot(x_step, y_step, color="#111827", linewidth=1.8)
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.25)
            if row == 0:
                title = scenario.replace("_", " ")
                if scenario == "few_turn_lower_accumulated_context":
                    title = "few turns, lower accumulated context"
                ax.set_title(title)
            if row == 2:
                ax.set_xlabel("Inference time (minutes)")

    max_time_min = df["end_time_s"].max() / 60.0
    tick_step = 0.5 if max_time_min <= 5 else 1.0
    ticks = np.arange(0, max_time_min + tick_step, tick_step)
    for ax in axes.flatten():
        ax.set_xlim(0, max_time_min)
        ax.set_xticks(ticks)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=colors["prefill"], alpha=0.6, label="prefill"),
        plt.Rectangle((0, 0), 1, 1, color=colors["decode"], alpha=0.6, label="decode"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.995))
    fig.suptitle(
        "Theoretical resource curves: many accumulated turns vs few accumulated turns",
        y=1.025,
        fontsize=14,
    )
    fig.text(
        0.5,
        0.01,
        f"Model={MODEL.name}, TP={HARDWARE.tp_size}, per-GPU peak={HARDWARE.compute_tflops_per_gpu:.0f} TFLOP/s "
        f"and {HARDWARE.bandwidth_gb_s_per_gpu:.0f} GB/s. Compute row shows chunk work, not achieved throughput.",
        ha="center",
        fontsize=8.5,
    )
    plt.tight_layout(rect=[0, 0.035, 1, 0.965])
    out = OUT_DIR / "fig9_long_vs_short_context_resource_curves.png"
    plt.savefig(out, dpi=220, bbox_inches="tight")
    plt.close()
    print(out)


def write_summary(df: pd.DataFrame) -> None:
    summary = (
        df.groupby("scenario", as_index=False)
        .agg(
            total_time_min=("time_s", lambda s: s.max() / 60.0),
            final_context_tokens=("context_tokens", "max"),
            peak_kv_gb_per_gpu=("resident_kv_gb_per_gpu", "max"),
            peak_compute_work_tflop_per_gpu=("compute_work_tflop_per_gpu", "max"),
            peak_compute_tflops_per_gpu=("compute_tflops_per_gpu", "max"),
            peak_memory_bandwidth_gb_s_per_gpu=("memory_bandwidth_gb_s_per_gpu", "max"),
            peak_kv_memory_bandwidth_gb_s_per_gpu=("kv_memory_bandwidth_gb_s_per_gpu", "max"),
        )
    )
    out = OUT_DIR / "long_vs_short_context_resource_summary.csv"
    summary.to_csv(out, index=False)
    print(out)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_assumptions()
    df = build_curves()
    write_summary(df)
    plot_curves(df)


if __name__ == "__main__":
    main()
