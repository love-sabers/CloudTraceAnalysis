#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis_outputs" / "decode_weight_kv_theory"

BYTES_PER_GB = 1_000_000_000
FLOPS_PER_TFLOPS = 1_000_000_000_000

# Large-model case: Qwen3-Coder-480B-A35B.
# The active-parameter count is used for prefill recomputation because MoE only
# activates a subset of experts per token. KV bytes are BF16 logical KV bytes.
MODEL = {
    "model": "Qwen3-Coder-480B-A35B",
    "active_params_b": 35.0,
    "layers": 62,
    "hidden_size": 6144,
    "kv_heads": 8,
    "head_dim": 128,
    "kv_bytes_per_token_bf16": 253_952,
    "source": "Qwen3-Coder-480B-A35B public config/model card and local model_node_kv_thresholds table",
}

TP_SIZES = [1, 2, 4, 8]
BANDWIDTH_GB_S = np.arange(50, 901, 50)

# Dense Tensor Core FP16/BF16 peak throughput without sparsity where possible.
GPU_COMPUTE = [
    {"gpu": "T4", "compute_tflops": 65.0, "source": "NVIDIA T4 public specs"},
    {"gpu": "L4", "compute_tflops": 121.0, "source": "NVIDIA L4 public specs"},
    {"gpu": "A30", "compute_tflops": 165.0, "source": "NVIDIA A30 public specs"},
    {"gpu": "A100/A800", "compute_tflops": 312.0, "source": "NVIDIA A100/A800-class public specs"},
    {"gpu": "L40S", "compute_tflops": 362.0, "source": "NVIDIA L40S public specs"},
    {"gpu": "H100/H800", "compute_tflops": 989.0, "source": "NVIDIA H100/H800-class public specs"},
    {"gpu": "H200", "compute_tflops": 989.0, "source": "NVIDIA H200 public specs"},
    {"gpu": "B200", "compute_tflops": 2250.0, "source": "NVIDIA B200 public specs"},
]


def context_threshold_tokens(bandwidth_gb_s: float, compute_tflops: float, tp_size: int) -> float:
    """Return N where reading existing sharded KV becomes no slower than prefill recompute.

    Per-GPU model:
      read_time = N * (kv_bytes_per_token / TP) / bandwidth
      prefill_time = N * (2 * active_params / TP) / compute
                   + N^2 * (4 * layers * hidden / TP) / compute

    Under ideal TP sharding, the 1/TP term appears on both sides. This means
    the threshold is TP-invariant unless communication, imbalance, or unsharded
    KV traffic is added.
    """

    bandwidth_b_s = bandwidth_gb_s * BYTES_PER_GB
    compute_flops_s = compute_tflops * FLOPS_PER_TFLOPS
    per_gpu_kv_bytes = MODEL["kv_bytes_per_token_bf16"] / tp_size
    per_gpu_linear_flops = 2 * MODEL["active_params_b"] * 1e9 / tp_size
    per_gpu_attention_flops_n2 = 4 * MODEL["layers"] * MODEL["hidden_size"] / tp_size

    read_time_per_token = per_gpu_kv_bytes / bandwidth_b_s
    linear_prefill_time_per_token = per_gpu_linear_flops / compute_flops_s
    attention_prefill_time_per_n2 = per_gpu_attention_flops_n2 / compute_flops_s

    if linear_prefill_time_per_token >= read_time_per_token:
        return 1.0
    return max(
        (read_time_per_token - linear_prefill_time_per_token) / attention_prefill_time_per_n2,
        1.0,
    )


def build_grid() -> pd.DataFrame:
    rows = []
    for tp in TP_SIZES:
        for gpu in GPU_COMPUTE:
            for bandwidth in BANDWIDTH_GB_S:
                threshold = context_threshold_tokens(
                    bandwidth_gb_s=float(bandwidth),
                    compute_tflops=gpu["compute_tflops"],
                    tp_size=tp,
                )
                rows.append(
                    {
                        "model": MODEL["model"],
                        "tp_size": tp,
                        "gpu": gpu["gpu"],
                        "compute_tflops": gpu["compute_tflops"],
                        "bandwidth_gb_s": bandwidth,
                        "context_threshold_tokens": threshold,
                    }
                )
    df = pd.DataFrame(rows)
    out = OUT_DIR / "kv_read_vs_prefill_threshold_by_tp_grid.csv"
    df.to_csv(out, index=False)
    print(out)
    return df


def write_assumptions() -> None:
    rows = []
    for gpu in GPU_COMPUTE:
        rows.append(
            {
                **MODEL,
                "gpu": gpu["gpu"],
                "compute_tflops": gpu["compute_tflops"],
                "gpu_source": gpu["source"],
                "tp_sizes": ",".join(str(x) for x in TP_SIZES),
                "bandwidth_range_gb_s": "50..900 step 50",
                "read_time": "N * (kv_bytes_per_token / TP) / bandwidth",
                "prefill_time": "N * (2 * active_params / TP) / compute + N^2 * (4 * layers * hidden_size / TP) / compute",
                "threshold_definition": "minimum context length N where reading existing sharded KV cache is no slower than recomputing KV by prefill",
                "tp_note": "Ideal TP sharding makes this threshold TP-invariant unless communication or unsharded KV traffic is modeled.",
            }
        )
    out = OUT_DIR / "kv_read_vs_prefill_threshold_by_tp_assumptions.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(out)


def plot_heatmap(df: pd.DataFrame) -> None:
    gpu_order = [x["gpu"] for x in GPU_COMPUTE]
    compute_by_gpu = {x["gpu"]: x["compute_tflops"] for x in GPU_COMPUTE}
    fig, axes = plt.subplots(2, 2, figsize=(13.8, 8.8), sharex=True, sharey=True)
    axes_flat = axes.flatten()

    vmax = max(10.0, float(df["context_threshold_tokens"].max()))
    norm = LogNorm(vmin=1.0, vmax=vmax)
    last_mesh = None

    for ax, tp in zip(axes_flat, TP_SIZES):
        part = df[df["tp_size"] == tp].copy()
        pivot = (
            part.pivot(index="gpu", columns="bandwidth_gb_s", values="context_threshold_tokens")
            .reindex(gpu_order)
            .sort_index(key=lambda idx: [compute_by_gpu[x] for x in idx])
        )
        z = pivot.to_numpy()
        x_edges = np.r_[BANDWIDTH_GB_S - 25, BANDWIDTH_GB_S[-1] + 25]
        y_edges = np.arange(len(pivot.index) + 1)
        last_mesh = ax.pcolormesh(x_edges, y_edges, z, shading="auto", cmap="viridis", norm=norm)

        ax.set_title(f"TP={tp}")
        ax.set_yticks(np.arange(len(pivot.index)) + 0.5)
        ax.set_yticklabels([f"{gpu}\n{compute_by_gpu[gpu]:.0f} TF" for gpu in pivot.index])
        ax.set_xlim(50, 900)
        ax.grid(True, axis="x", color="white", alpha=0.18, linewidth=0.6)
        for x in BANDWIDTH_GB_S:
            ax.axvline(x, color="white", alpha=0.05, linewidth=0.5)

    fig.suptitle(
        "Context threshold: read existing KV cache vs recompute prefill KV",
        fontsize=14,
        y=0.98,
    )
    fig.supxlabel("KV cache read bandwidth per GPU (GB/s)", y=0.075)
    fig.supylabel("NVIDIA GPU dense FP16/BF16 Tensor Core peak", x=0.025)
    cax = fig.add_axes([0.895, 0.18, 0.018, 0.66])
    cbar = fig.colorbar(last_mesh, cax=cax)
    cbar.set_label("Break-even context length (tokens, log scale)")
    fig.text(
        0.5,
        0.025,
        f"Model: {MODEL['model']}; BF16 KV; bandwidth sweep 50..900 GB/s, step 50. "
        "Ideal TP sharding makes TP panels equal unless communication/non-sharded traffic is added.",
        ha="center",
        fontsize=8.5,
    )
    fig.subplots_adjust(left=0.13, right=0.86, bottom=0.15, top=0.91, hspace=0.25, wspace=0.08)
    out = OUT_DIR / "fig7_kv_read_vs_prefill_threshold_by_tp_heatmap.png"
    plt.savefig(out, dpi=220, bbox_inches="tight")
    plt.close()
    print(out)


def write_summary(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(["tp_size", "gpu"], as_index=False)
        .agg(
            min_threshold_tokens=("context_threshold_tokens", "min"),
            max_threshold_tokens=("context_threshold_tokens", "max"),
        )
        .sort_values(["tp_size", "max_threshold_tokens", "gpu"])
    )
    out = OUT_DIR / "kv_read_vs_prefill_threshold_by_tp_summary.csv"
    summary.to_csv(out, index=False)
    print(out)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_assumptions()
    df = build_grid()
    write_summary(df)
    plot_heatmap(df)


if __name__ == "__main__":
    main()
