#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_model_node_kv_thresholds import (  # noqa: E402
    BYTES_PER_GB,
    MODELS,
    GPUS,
    WEIGHT_BYTES,
    evaluate_plan,
)


@dataclass(frozen=True)
class GpuPerfSpec:
    hbm_bandwidth_tbps: float
    bf16_tflops: float


GPU_PERF = {
    "A100": GpuPerfSpec(hbm_bandwidth_tbps=2.0, bf16_tflops=312.0),
    "H100NVL": GpuPerfSpec(hbm_bandwidth_tbps=3.9, bf16_tflops=989.0),
    "B200": GpuPerfSpec(hbm_bandwidth_tbps=8.0, bf16_tflops=2250.0),
}

TP_SWEEP = [1, 2, 4, 8, 12, 18, 24, 36, 72]
PER_DP_GROUP_BATCHES = np.arange(1, 4097, dtype=int)
CONTEXT_SWEEP = [8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576]
SELECTED_CURVE_CONTEXTS = [32768, 1048576]
EFFICIENCY_B0 = 16.0
MAX_COMPUTE_EFFICIENCY = 0.72
COMM_OVERHEAD_US = 30.0
OUT_DIR = ROOT / "analysis_outputs" / "concurrency_sweet_points"
IGNORE_HBM_LIMIT = False


def compute_efficiency(per_replica_batch: int) -> float:
    return MAX_COMPUTE_EFFICIENCY * (1.0 - np.exp(-per_replica_batch / EFFICIENCY_B0))


def active_params_b(model) -> float:
    if model.active_params_b is not None:
        return model.active_params_b
    return model.params_b


def expert_unique_fraction(model, per_replica_batch: int) -> float:
    if not model.is_moe or not model.num_experts or not model.experts_per_token:
        return 1.0
    p = min(model.experts_per_token / model.num_experts, 1.0)
    return 1.0 - (1.0 - p) ** per_replica_batch


def step_latency_seconds(model, gpu, tp_size: int, dp_size: int, per_replica_batch: int, context_tokens: int) -> dict:
    perf = GPU_PERF[gpu.name]
    total_concurrency = per_replica_batch * dp_size
    eff = compute_efficiency(per_replica_batch)

    dense_weight_bytes = model.dense_params_b * 1e9 * WEIGHT_BYTES
    if model.is_moe:
        weight_bytes = dense_weight_bytes + model.expert_params_b * 1e9 * WEIGHT_BYTES * expert_unique_fraction(
            model, per_replica_batch
        )
    else:
        weight_bytes = model.params_b * 1e9 * WEIGHT_BYTES

    weight_time = weight_bytes / (tp_size * perf.hbm_bandwidth_tbps * 1e12)
    flops = 2.0 * active_params_b(model) * 1e9 * per_replica_batch
    compute_time = flops / (tp_size * perf.bf16_tflops * 1e12 * max(eff, 1e-6))
    kv_bytes = per_replica_batch * context_tokens * model.kv_bytes_per_token
    kv_time = kv_bytes / (tp_size * perf.hbm_bandwidth_tbps * 1e12)
    overhead_time = COMM_OVERHEAD_US * 1e-6 * np.log2(max(tp_size, 1))

    step_time = max(weight_time, compute_time, kv_time) + overhead_time
    throughput = total_concurrency / step_time
    return {
        "per_replica_batch": per_replica_batch,
        "compute_efficiency": eff,
        "weight_time_ms": weight_time * 1e3,
        "compute_time_ms": compute_time * 1e3,
        "kv_time_ms": kv_time * 1e3,
        "overhead_time_ms": overhead_time * 1e3,
        "step_time_ms": step_time * 1e3,
        "throughput_tokens_per_s": throughput,
    }


def build_rows(ignore_hbm_limit: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    curve_rows = []
    for gpu in GPUS:
        dep = {
            "deployment": f"{gpu.name}x72",
            "gpu_model": gpu.name,
            "gpus_per_node": 72,
            "hbm_gb_per_gpu": gpu.hbm_gb,
            "node_hbm_gb": gpu.hbm_gb * 72,
            "usable_hbm_gb": gpu.hbm_gb * 72 * 0.90,
            "node_source": gpu.source,
        }
        for model in MODELS:
            for tp_size in TP_SWEEP:
                dp_size = 72 // tp_size
                plan = {
                    "tp_size": tp_size,
                    "dp_size": dp_size,
                    "ep_size": 72 if model.is_moe else 1,
                    "kv_replication_factor": 1,
                    "parallelism": f"TP{tp_size}/DP{dp_size}/EP{72 if model.is_moe else 1}",
                }
                capacity = evaluate_plan(model, dep, plan)
                for context_tokens in CONTEXT_SWEEP:
                    rows = []
                    for per_replica_batch in PER_DP_GROUP_BATCHES:
                        total_concurrency = int(per_replica_batch * dp_size)
                        requested_kv_tokens_per_dp_group = int(per_replica_batch * context_tokens)
                        capacity_feasible = (
                            capacity["feasible_after_tp_dp_ep_weights"]
                            and requested_kv_tokens_per_dp_group <= capacity["max_resident_kv_tokens_per_dp_replica"]
                        )
                        if not ignore_hbm_limit and not capacity_feasible:
                            continue
                        metrics = step_latency_seconds(model, gpu, tp_size, dp_size, int(per_replica_batch), context_tokens)
                        row = {
                            "context_tokens": context_tokens,
                            "gpu_model": gpu.name,
                            "deployment": dep["deployment"],
                            "model": model.name,
                            "tp_size": tp_size,
                            "dp_size": dp_size,
                            "ep_size": plan["ep_size"],
                            "parallelism": plan["parallelism"],
                            "batch_per_dp_group": int(per_replica_batch),
                            "total_concurrency": int(total_concurrency),
                            "requested_kv_tokens_per_dp_group": requested_kv_tokens_per_dp_group,
                            "capacity_feasible": bool(capacity_feasible),
                            "max_kv_tokens_per_gpu": capacity["max_resident_kv_tokens_per_gpu"],
                            "max_kv_tokens_node": capacity["max_resident_kv_tokens"],
                            "max_kv_tokens_per_dp_replica": capacity["max_resident_kv_tokens_per_dp_replica"],
                            **metrics,
                        }
                        rows.append(row)
                        if context_tokens in SELECTED_CURVE_CONTEXTS:
                            curve_rows.append(row)
                    if rows:
                        summary_rows.extend(summarize_one_curve(rows))
    return pd.DataFrame(summary_rows), pd.DataFrame(curve_rows)


def summarize_one_curve(rows: list[dict]) -> list[dict]:
    part = pd.DataFrame(rows)
    first = rows[0]
    peak = part["throughput_tokens_per_s"].max()
    out = []
    for target in [0.90, 0.95]:
        hit = part[part["throughput_tokens_per_s"] >= target * peak].sort_values("batch_per_dp_group").head(1)
        if hit.empty:
            continue
        row = hit.iloc[0].to_dict()
        out.append(
            {
                "context_tokens": int(first["context_tokens"]),
                "gpu_model": first["gpu_model"],
                "deployment": first["deployment"],
                "model": first["model"],
                "tp_size": int(first["tp_size"]),
                "dp_size": int(first["dp_size"]),
                "ep_size": int(first["ep_size"]),
                "parallelism": first["parallelism"],
                "target_fraction": target,
                "sweet_total_concurrency": int(row["total_concurrency"]),
                "sweet_batch_per_dp_group": int(row["batch_per_dp_group"]),
                "peak_throughput_tokens_per_s": peak,
                "sweet_throughput_tokens_per_s": row["throughput_tokens_per_s"],
                "sweet_normalized_throughput": row["throughput_tokens_per_s"] / peak,
                "dominant_time_at_sweet": max(
                    ["weight_time_ms", "compute_time_ms", "kv_time_ms"],
                    key=lambda col: row[col],
                ).replace("_time_ms", ""),
            }
        )
    return out


def plot_sweet_heatmap(summary: pd.DataFrame, target: float, context_tokens: int) -> None:
    model_order = [m.name for m in MODELS]
    fig, axes = plt.subplots(1, len(GPUS), figsize=(26, 10), sharey=True, constrained_layout=True)
    for ax, gpu in zip(axes, GPUS):
        part = summary[(summary["gpu_model"] == gpu.name) & (summary["target_fraction"] == target) & (summary["context_tokens"] == context_tokens)]
        pivot = part.pivot(index="model", columns="tp_size", values="sweet_batch_per_dp_group").reindex(
            index=model_order, columns=TP_SWEEP
        )
        total_pivot = part.pivot(index="model", columns="tp_size", values="sweet_total_concurrency").reindex(
            index=model_order, columns=TP_SWEEP
        )
        label_plan = part.pivot(index="model", columns="tp_size", values="parallelism").reindex(
            index=model_order, columns=TP_SWEEP
        )

        values = pivot.to_numpy(dtype=float)
        color_values = np.full_like(values, np.nan, dtype=float)
        positive = values > 0
        color_values[positive] = np.log10(values[positive])

        cmap = plt.cm.mako if hasattr(plt.cm, "mako") else plt.cm.viridis
        cmap = cmap.copy()
        cmap.set_bad("#d9d9d9")
        im = ax.imshow(color_values, cmap=cmap, aspect="auto")
        ax.set_title(f"{gpu.name}x72")
        ax.set_xlabel("TP size")
        ax.set_xticks(np.arange(len(TP_SWEEP)))
        ax.set_xticklabels([str(tp) for tp in TP_SWEEP])
        ax.set_yticks(np.arange(len(model_order)))
        ax.set_yticklabels(model_order)

        for i, model in enumerate(model_order):
            for j, tp_size in enumerate(TP_SWEEP):
                value = pivot.loc[model, tp_size]
                if pd.isna(value):
                    label = "n/a"
                else:
                    total_value = int(total_pivot.loc[model, tp_size])
                    label = f"B={int(value)}\nC={total_value}\n{label_plan.loc[model, tp_size]}"
                ax.text(
                    j,
                    i,
                    label,
                    ha="center",
                    va="center",
                    color="#555555",
                    fontsize=7.0,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white", alpha=0.75)],
                )
    axes[0].set_ylabel("Open large model")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist())
    cbar.set_label(f"log10(min batch per DP group for {int(target * 100)}% peak throughput)")
    fig.suptitle(f"72-GPU Concurrency Sweet Point: Min Batch per DP Group for {int(target * 100)}% Peak (Context={context_tokens:,})", fontsize=16)
    fig.text(
        0.5,
        -0.01,
        f"Analytical decode model {'without' if IGNORE_HBM_LIMIT else 'with'} HBM capacity limits. Context={context_tokens:,} tokens; TP*DP=72; MoE EP=72; B=batch per DP group, C=total concurrency.",
        ha="center",
        va="top",
        fontsize=10,
    )
    fig.savefig(OUT_DIR / f"72gpu_concurrency_sweet_point_ctx{context_tokens}_p{int(target * 100)}.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def plot_selected_curves(curves: pd.DataFrame, summary: pd.DataFrame) -> None:
    selected_models = ["Qwen3-235B-A22B", "DeepSeek-V3/R1-671B", "Kimi-K2-1T-A32B", "DeepSeek-V4-Pro-1.6T"]
    selected_tp = [1, 8, 72]
    tp_colors = {1: "#1f77b4", 8: "#ff7f0e", 72: "#2ca02c"}
    fig, axes = plt.subplots(len(selected_models), len(GPUS), figsize=(18, 12), sharex=True, sharey=True, constrained_layout=True)
    for row, model in enumerate(selected_models):
        for col, gpu in enumerate(GPUS):
            ax = axes[row, col]
            for tp_size in selected_tp:
                for context_tokens in SELECTED_CURVE_CONTEXTS:
                    part = curves[
                        (curves["model"] == model)
                        & (curves["gpu_model"] == gpu.name)
                        & (curves["tp_size"] == tp_size)
                        & (curves["context_tokens"] == context_tokens)
                    ].copy()
                    if part.empty:
                        continue
                    peak = part["throughput_tokens_per_s"].max()
                    ax.plot(
                        part["total_concurrency"],
                        part["throughput_tokens_per_s"] / peak,
                        label=f"TP{tp_size}/DP{72 // tp_size}, ctx={context_tokens//1024}K",
                        linewidth=1.5,
                        color=tp_colors[tp_size],
                        linestyle="--" if context_tokens == max(SELECTED_CURVE_CONTEXTS) else "-",
                    )
            ax.axhline(0.90, color="#777777", linestyle="--", linewidth=0.9)
            ax.axhline(0.95, color="#444444", linestyle=":", linewidth=0.9)
            ax.set_xscale("log")
            ax.grid(True, which="both", alpha=0.25)
            if row == 0:
                ax.set_title(f"{gpu.name}x72")
            if col == 0:
                ax.set_ylabel(model)
            if row == len(selected_models) - 1:
                ax.set_xlabel("Total batch / total concurrency")
            ax.legend(frameon=False, fontsize=7)
    fig.suptitle("Normalized Decode Throughput vs Total Batch", fontsize=16)
    fig.savefig(OUT_DIR / "72gpu_concurrency_throughput_curves.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_readme() -> None:
    if IGNORE_HBM_LIMIT:
        variant_note = [
            "This variant intentionally disables HBM capacity constraints. It does not truncate by KV cache capacity and does not mark weight/KV residency as infeasible.",
        ]
    else:
        variant_note = [
            "This variant applies the HBM capacity constraint from `analysis_outputs/model_node_kv_thresholds`.",
            "A point is kept only when `batch_per_dp_group * context_tokens <= max_kv_tokens_per_dp_replica` after TP/DP/EP weight placement.",
        ]
    lines = [
        "# Concurrency sweet-point analysis",
        "",
        "This is an analytical decode-stage model, not an inference benchmark.",
        "",
        *variant_note,
        "",
        "## Model",
        "",
        "For each 72-GPU deployment and TP choice, `DP = 72 / TP`; MoE uses `EP = 72`.",
        "",
        "Per-step latency is modeled as:",
        "",
        "```text",
        "step_latency = max(weight_read_time, compute_time, kv_read_time) + communication_overhead",
        "node_decode_throughput = total_concurrency / step_latency",
        "```",
        "",
        "The scan variable is integer `batch_per_dp_group`. Total node concurrency is derived as `batch_per_dp_group * DP`.",
        "",
        "Larger per-DP-group batch improves throughput by amortizing weight reads and increasing GEMM efficiency. The gains saturate when compute, KV bandwidth, or communication overhead dominates.",
        "",
        "## Outputs",
        "",
        "- `72gpu_concurrency_curves.csv.gz`: compressed full throughput curves",
        "- `72gpu_concurrency_sweet_points.csv`: minimum per-DP-group batch and derived total concurrency for 90% and 95% peak throughput",
        "- `72gpu_concurrency_sweet_point_ctx*_p90.png`: 90% sweet-point heatmaps for each context length",
        "- `72gpu_concurrency_sweet_point_ctx*_p95.png`: 95% sweet-point heatmaps for each context length",
        "- `72gpu_concurrency_throughput_curves.png`: normalized throughput curves for selected large MoE models",
        "",
        "## Assumptions",
        "",
        f"- Context lengths for KV reads: `{CONTEXT_SWEEP}` tokens",
        "- Weights and KV cache use bf16/fp16.",
        "- GPU performance assumptions are encoded in `GPU_PERF` in the script.",
        "- MoE expert weight reads use an independent expert-activation approximation to capture diminishing weight-read amortization.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    global OUT_DIR, IGNORE_HBM_LIMIT
    parser = argparse.ArgumentParser(description="Analyze integer per-DP-group concurrency sweet points on 72-GPU nodes.")
    parser.add_argument(
        "--ignore-hbm-limit",
        action="store_true",
        help="Do not truncate the batch scan by available HBM KV capacity.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to the matching analysis_outputs variant.",
    )
    args = parser.parse_args()
    IGNORE_HBM_LIMIT = args.ignore_hbm_limit
    OUT_DIR = args.out_dir or (
        ROOT / "analysis_outputs" / ("concurrency_sweet_points_no_hbm_limit" if IGNORE_HBM_LIMIT else "concurrency_sweet_points")
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary, curves = build_rows(ignore_hbm_limit=IGNORE_HBM_LIMIT)
    curves.to_csv(OUT_DIR / "72gpu_concurrency_curves.csv.gz", index=False, compression="gzip")
    summary.to_csv(OUT_DIR / "72gpu_concurrency_sweet_points.csv", index=False)
    for context_tokens in CONTEXT_SWEEP:
        plot_sweet_heatmap(summary, 0.90, context_tokens)
        plot_sweet_heatmap(summary, 0.95, context_tokens)
    plot_selected_curves(curves, summary)
    write_readme()
    print(f"Sweet-point rows: {len(summary)}")
    print(f"Representative curve rows: {len(curves)}")
    print(f"\nOutputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
