#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis_outputs" / "decode_weight_kv_theory"
MODEL_NODE_DIR = ROOT / "analysis_outputs" / "model_node_kv_thresholds"

BYTES_PER_GB = 1_000_000_000
BYTES_PER_MB = 1_000_000
A800_HBM_GB_S = 2039.0
A800_FP16_PEAK_TFLOP_S = 312.0
ATTN_EFFECTIVE_COMPUTE_FRACTION = 0.10
LARGE_CONTEXTS = [4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576]


def savefig(path: Path, tight: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if tight:
        plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight")
    plt.close()
    print(path)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    models = pd.read_csv(OUT_DIR / "model_configs.csv")
    baseline = pd.read_csv(OUT_DIR / "theory_baseline_b1_fp16.csv")
    gpu = pd.read_csv(OUT_DIR / "gpu_assumptions.csv")
    return models, baseline, gpu


def palette(names: list[str]) -> dict[str, tuple[float, float, float, float]]:
    cmap = plt.get_cmap("tab10")
    return {name: cmap(i % 10) for i, name in enumerate(names)}


def plot_weight_vs_kv(baseline: pd.DataFrame) -> None:
    models = list(dict.fromkeys(baseline["model"]))
    colors = palette(models)

    fig, ax = plt.subplots(figsize=(10.8, 6.3))
    for model in models:
        part = baseline[baseline["model"] == model].sort_values("context_len")
        color = colors[model]
        ax.plot(
            part["context_len"],
            part["kv_read_mb_fp16_b1"] / 1000,
            marker="o",
            linewidth=2.0,
            markersize=4,
            color=color,
            label=f"{model} KV",
        )
        ax.hlines(
            part["weight_read_gb_fp16_b1"].iloc[0],
            xmin=part["context_len"].min(),
            xmax=part["context_len"].max(),
            linestyle="--",
            linewidth=1.2,
            color=color,
            alpha=0.55,
        )

    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("Context length")
    ax.set_ylabel("Read volume per generated token (GB, decimal)")
    ax.set_title("Decode theoretical read bytes: weights vs KV cache")
    ax.grid(True, which="both", alpha=0.22)
    ax.text(
        0.01,
        0.99,
        "Solid lines: KV reads. Dashed horizontal lines: FP16 weight reads.",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none"},
    )
    ax.legend(ncol=2, fontsize=8, frameon=False)
    savefig(OUT_DIR / "fig1_weight_vs_kv_bytes.png")


def plot_kv_weight_ratio(baseline: pd.DataFrame) -> None:
    models = list(dict.fromkeys(baseline["model"]))
    colors = palette(models)

    fig, ax = plt.subplots(figsize=(10.5, 5.9))
    for model in models:
        part = baseline[baseline["model"] == model].sort_values("context_len")
        ax.plot(
            part["context_len"],
            part["kv_to_weight_ratio"],
            marker="o",
            linewidth=2.0,
            markersize=4,
            color=colors[model],
            label=model,
        )

    ax.axhline(1.0, color="#202020", linestyle="--", linewidth=1.1)
    ax.text(1050, 1.08, "KV reads = weight reads", fontsize=9)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("Context length")
    ax.set_ylabel("KV read bytes / weight read bytes")
    ax.set_title("When does KV traffic overtake weight traffic? (batch=1, FP16)")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend(ncol=2, fontsize=8, frameon=False)
    savefig(OUT_DIR / "fig2_kv_weight_ratio.png")


def plot_attention_ai(baseline: pd.DataFrame, models: pd.DataFrame) -> None:
    ai = baseline.groupby("model", as_index=False)["attn_ai_flop_per_byte_fp16"].first()
    ai = ai.merge(models[["model", "attention_family"]], on="model", how="left")
    ai = ai.sort_values(["attn_ai_flop_per_byte_fp16", "model"])

    family_colors = {"MHA": "#6b7280", "GQA": "#2563eb", "MQA": "#059669"}
    colors = [family_colors.get(x, "#7c3aed") for x in ai["attention_family"]]

    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    bars = ax.barh(ai["model"], ai["attn_ai_flop_per_byte_fp16"], color=colors)
    for bar, value in zip(bars, ai["attn_ai_flop_per_byte_fp16"]):
        ax.text(value + 0.08, bar.get_y() + bar.get_height() / 2, f"{value:.1f}", va="center", fontsize=9)

    ax.set_xlabel("Attention arithmetic intensity (FLOPs per KV byte)")
    ax.set_title("Decode attention AI from Q heads / KV heads (FP16 KV)")
    ax.grid(axis="x", alpha=0.22)
    ax.set_xlim(0, max(ai["attn_ai_flop_per_byte_fp16"]) * 1.22)
    legend_handles = [
        plt.Line2D([0], [0], color=color, lw=8, label=family)
        for family, color in family_colors.items()
        if family in set(ai["attention_family"])
    ]
    ax.legend(handles=legend_handles, frameon=False, loc="lower right")
    savefig(OUT_DIR / "fig3_attention_arithmetic_intensity.png")


def add_roofline_columns(baseline: pd.DataFrame, models: pd.DataFrame) -> pd.DataFrame:
    df = baseline.merge(
        models[["model", "layers", "n_q_heads", "n_kv_heads", "head_dim"]],
        on="model",
        how="left",
    ).copy()
    df["kv_read_gb"] = df["kv_read_mb_fp16_b1"] / 1000
    df["kv_memory_time_ms"] = df["kv_read_gb"] / A800_HBM_GB_S * 1000
    df["attention_flops"] = (
        4
        * df["layers"]
        * df["context_len"]
        * df["n_q_heads"]
        * df["head_dim"]
    )
    effective_tflops = A800_FP16_PEAK_TFLOP_S * ATTN_EFFECTIVE_COMPUTE_FRACTION
    df["attention_compute_time_ms"] = df["attention_flops"] / (effective_tflops * 1e12) * 1000
    return df


def plot_roofline(baseline: pd.DataFrame, models: pd.DataFrame) -> pd.DataFrame:
    df = add_roofline_columns(baseline, models)
    model_names = list(dict.fromkeys(df["model"]))

    fig, axes = plt.subplots(2, 4, figsize=(13.5, 6.8), sharex=True, sharey=True)
    axes_flat = axes.flatten()
    for ax, model in zip(axes_flat, model_names):
        part = df[df["model"] == model].sort_values("context_len")
        ax.plot(
            part["context_len"],
            part["kv_memory_time_ms"],
            marker="o",
            linewidth=1.9,
            markersize=3.5,
            label="KV HBM time",
            color="#dc2626",
        )
        ax.plot(
            part["context_len"],
            part["attention_compute_time_ms"],
            marker="s",
            linewidth=1.7,
            markersize=3.3,
            label="Attention compute time",
            color="#2563eb",
        )
        ax.set_title(model, fontsize=9)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.grid(True, which="both", alpha=0.20)

    for ax in axes_flat[len(model_names) :]:
        ax.axis("off")

    fig.suptitle(
        "Roofline-style decode attention estimate: KV memory time vs QK/AV compute time",
        y=0.98,
        fontsize=13,
    )
    fig.supxlabel("Context length", y=0.075)
    fig.supylabel("Estimated time per generated token (ms)", x=0.03)
    axes_flat[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.text(
        0.5,
        0.035,
        f"Assumptions: HBM={A800_HBM_GB_S:.0f} GB/s, attention effective compute="
        f"{ATTN_EFFECTIVE_COMPUTE_FRACTION:.0%} of {A800_FP16_PEAK_TFLOP_S:.0f} TFLOP/s FP16 peak.",
        ha="center",
        fontsize=8.5,
    )
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.16, top=0.86, hspace=0.36, wspace=0.08)
    savefig(OUT_DIR / "fig4_roofline_kv_memory_vs_attention_compute.png", tight=False)
    return df


def write_roofline_table(df: pd.DataFrame) -> None:
    keep = [
        "model",
        "context_len",
        "kv_read_gb",
        "kv_memory_time_ms",
        "attention_flops",
        "attention_compute_time_ms",
    ]
    out = df[keep].copy()
    out["kv_read_gb"] = out["kv_read_gb"].round(4)
    out["kv_memory_time_ms"] = out["kv_memory_time_ms"].round(6)
    out["attention_compute_time_ms"] = out["attention_compute_time_ms"].round(6)
    out.to_csv(OUT_DIR / "roofline_estimates.csv", index=False)
    print(OUT_DIR / "roofline_estimates.csv")


def load_large_model_specs() -> pd.DataFrame:
    src = pd.read_csv(MODEL_NODE_DIR / "model_node_kv_thresholds.csv")
    specs = src[(src["deployment"] == "A100x1") & (src["policy"] == "capacity_opt")].copy()
    specs = specs.drop_duplicates("model", keep="first")
    numeric_cols = [
        "params_b",
        "active_params_b",
        "dense_params_b_config",
        "expert_params_b_config",
        "layers",
        "kv_heads",
        "head_dim",
        "mla_kv_lora_rank",
        "mla_qk_rope_head_dim",
        "kv_bytes_per_token_bf16",
    ]
    for col in numeric_cols:
        specs[col] = pd.to_numeric(specs[col], errors="coerce")

    specs["active_or_total_params_b"] = specs["active_params_b"].fillna(specs["params_b"])
    specs["weight_total_gb_bf16"] = specs["params_b"] * 2
    specs["weight_active_gb_bf16"] = specs["active_or_total_params_b"] * 2
    specs["is_moe"] = specs["active_params_b"].notna()
    specs["kv_mb_per_1k_tokens_bf16"] = specs["kv_bytes_per_token_bf16"] * 1000 / BYTES_PER_MB
    specs["crossover_total_context"] = (
        specs["weight_total_gb_bf16"] * BYTES_PER_GB / specs["kv_bytes_per_token_bf16"]
    )
    specs["crossover_active_context"] = (
        specs["weight_active_gb_bf16"] * BYTES_PER_GB / specs["kv_bytes_per_token_bf16"]
    )
    keep = [
        "model",
        "params_b",
        "active_params_b",
        "dense_params_b_config",
        "expert_params_b_config",
        "active_or_total_params_b",
        "is_moe",
        "layers",
        "kv_formula",
        "kv_heads",
        "head_dim",
        "mla_kv_lora_rank",
        "mla_qk_rope_head_dim",
        "kv_bytes_per_token_bf16",
        "kv_mb_per_1k_tokens_bf16",
        "weight_total_gb_bf16",
        "weight_active_gb_bf16",
        "crossover_total_context",
        "crossover_active_context",
        "model_source",
    ]
    return specs[keep].sort_values("params_b")


def build_large_model_theory(specs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, model in specs.iterrows():
        for context in LARGE_CONTEXTS:
            kv_read_gb = model["kv_bytes_per_token_bf16"] * context / BYTES_PER_GB
            rows.append(
                {
                    "model": model["model"],
                    "context_len": context,
                    "params_b": model["params_b"],
                    "active_params_b": model["active_params_b"],
                    "is_moe": model["is_moe"],
                    "kv_formula": model["kv_formula"],
                    "kv_read_gb_bf16": kv_read_gb,
                    "weight_total_gb_bf16": model["weight_total_gb_bf16"],
                    "weight_active_gb_bf16": model["weight_active_gb_bf16"],
                    "kv_to_total_weight_ratio": kv_read_gb / model["weight_total_gb_bf16"],
                    "kv_to_active_weight_ratio": kv_read_gb / model["weight_active_gb_bf16"],
                    "crossover_total_context": model["crossover_total_context"],
                    "crossover_active_context": model["crossover_active_context"],
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "large_model_weight_kv_theory.csv", index=False)
    print(OUT_DIR / "large_model_weight_kv_theory.csv")
    specs.to_csv(OUT_DIR / "large_model_configs.csv", index=False)
    print(OUT_DIR / "large_model_configs.csv")
    return df


def plot_large_ratio(df: pd.DataFrame) -> None:
    model_order = (
        df[["model", "params_b"]]
        .drop_duplicates()
        .sort_values("params_b")["model"]
        .tolist()
    )
    colors = palette(model_order)

    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    for model in model_order:
        part = df[df["model"] == model].sort_values("context_len")
        ax.plot(
            part["context_len"],
            part["kv_to_active_weight_ratio"],
            marker="o",
            linewidth=1.9,
            markersize=3.8,
            color=colors[model],
            label=model,
        )

    ax.axhline(1.0, color="#202020", linestyle="--", linewidth=1.1)
    ax.axvline(524288, color="#7f1d1d", linestyle=":", linewidth=1.4)
    ax.text(540000, 0.025, "524k context", rotation=90, fontsize=8.5, color="#7f1d1d")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("Context length")
    ax.set_ylabel("KV read bytes / active weight read bytes")
    ax.set_title("Large-model decode memory pressure: KV vs active weights")
    ax.grid(True, which="both", alpha=0.22)
    ax.legend(ncol=2, fontsize=7.4, frameon=False)
    savefig(OUT_DIR / "fig5_large_model_kv_active_weight_ratio.png")


def plot_large_crossover(specs: pd.DataFrame) -> None:
    plot_df = specs.sort_values("crossover_active_context", ascending=True).copy()
    y = np.arange(len(plot_df))
    height = 0.36

    fig, ax = plt.subplots(figsize=(11.6, 6.8))
    ax.barh(
        y - height / 2,
        plot_df["crossover_active_context"],
        height=height,
        color="#2563eb",
        label="active-weight crossover",
    )
    ax.barh(
        y + height / 2,
        plot_df["crossover_total_context"],
        height=height,
        color="#94a3b8",
        label="total-resident-weight crossover",
    )
    ax.axvline(524288, color="#7f1d1d", linestyle=":", linewidth=1.4)
    ax.text(545000, len(plot_df) - 0.7, "524k", fontsize=8.5, color="#7f1d1d")
    ax.set_xscale("log", base=10)
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["model"])
    ax.set_xlabel("Crossover context length (KV read bytes = weight read bytes)")
    ax.set_title("Large-model crossover depends on active vs total weight traffic")
    ax.grid(axis="x", which="both", alpha=0.22)
    ax.legend(frameon=False, loc="lower right")
    savefig(OUT_DIR / "fig6_large_model_crossover_contexts.png")


def write_large_model_summary(df: pd.DataFrame, specs: pd.DataFrame) -> None:
    at_524k = df[df["context_len"] == 524288].copy()
    at_524k = at_524k.sort_values("params_b")
    keep = [
        "model",
        "params_b",
        "active_params_b",
        "kv_formula",
        "kv_read_gb_bf16",
        "weight_active_gb_bf16",
        "weight_total_gb_bf16",
        "kv_to_active_weight_ratio",
        "kv_to_total_weight_ratio",
        "crossover_active_context",
        "crossover_total_context",
    ]
    summary = at_524k[keep].copy()
    for col in [
        "kv_read_gb_bf16",
        "weight_active_gb_bf16",
        "weight_total_gb_bf16",
        "kv_to_active_weight_ratio",
        "kv_to_total_weight_ratio",
        "crossover_active_context",
        "crossover_total_context",
    ]:
        summary[col] = summary[col].round(4)
    summary.to_csv(OUT_DIR / "large_model_524k_summary.csv", index=False)
    print(OUT_DIR / "large_model_524k_summary.csv")


def main() -> None:
    models, baseline, _ = load_data()
    plot_weight_vs_kv(baseline)
    plot_kv_weight_ratio(baseline)
    plot_attention_ai(baseline, models)
    roofline = plot_roofline(baseline, models)
    write_roofline_table(roofline)
    large_specs = load_large_model_specs()
    large_theory = build_large_model_theory(large_specs)
    plot_large_ratio(large_theory)
    plot_large_crossover(large_specs)
    write_large_model_summary(large_theory, large_specs)


if __name__ == "__main__":
    main()
