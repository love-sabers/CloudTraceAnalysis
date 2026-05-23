#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPOT_JOB_CSV = ROOT / "data" / "spot_gpu" / "job_info_df.csv"
GENAI_REQ_CSV = ROOT / "data" / "genai_full" / "lora_request_trace.csv"
OUT_DIR = ROOT / "analysis_outputs" / "duration_distribution"


def ensure_inputs() -> None:
    missing = [str(p) for p in [SPOT_JOB_CSV, GENAI_REQ_CSV] if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing input files: " + ", ".join(missing))


def duration_summary(df: pd.DataFrame, group_cols: list[str], value_col: str) -> pd.DataFrame:
    def q(v: pd.Series, p: float) -> float:
        return float(v.quantile(p))

    grouped = df.groupby(group_cols, dropna=False)[value_col]
    out = grouped.agg(
        count="count",
        mean_s="mean",
        std_s="std",
        min_s="min",
        p25_s=lambda s: q(s, 0.25),
        p50_s=lambda s: q(s, 0.50),
        p75_s=lambda s: q(s, 0.75),
        p90_s=lambda s: q(s, 0.90),
        p95_s=lambda s: q(s, 0.95),
        p99_s=lambda s: q(s, 0.99),
        max_s="max",
    ).reset_index()
    for col in ["mean_s", "p50_s", "p90_s", "p95_s", "p99_s", "max_s"]:
        out[col.replace("_s", "_h")] = out[col] / 3600.0
    return out


def load_spot_jobs() -> pd.DataFrame:
    cols = ["job_name", "organization", "gpu_model", "duration", "job_type"]
    df = pd.read_csv(SPOT_JOB_CSV, usecols=cols)
    df["duration_s"] = pd.to_numeric(df["duration"], errors="coerce")
    df = df[df["duration_s"].notna() & (df["duration_s"] > 0)].copy()
    df["duration_h"] = df["duration_s"] / 3600.0
    df["job_type"] = df["job_type"].fillna("UNKNOWN").astype(str)
    df["gpu_model"] = df["gpu_model"].fillna("UNKNOWN").astype(str)
    df["dataset"] = "spot_gpu_jobs"
    return df


def load_genai_requests() -> pd.DataFrame:
    cols = ["predict_type", "predict_status", "exec_time_seconds", "num_lora"]
    df = pd.read_csv(GENAI_REQ_CSV, usecols=cols)
    df["duration_s"] = pd.to_numeric(df["exec_time_seconds"], errors="coerce")
    df = df[df["duration_s"].notna() & (df["duration_s"] > 0)].copy()
    df["duration_h"] = df["duration_s"] / 3600.0
    df["predict_type"] = df["predict_type"].fillna("UNKNOWN").astype(str)
    df["predict_status"] = df["predict_status"].fillna("UNKNOWN").astype(str)
    df["dataset"] = "genai_requests"
    return df


def set_duration_ticks(ax: plt.Axes) -> None:
    ticks = [1, 10, 60, 600, 3600, 6 * 3600, 24 * 3600, 7 * 24 * 3600]
    labels = ["1s", "10s", "1m", "10m", "1h", "6h", "1d", "7d"]
    ax.set_xscale("log")
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.grid(True, which="both", axis="both", alpha=0.25)


def plot_hist_by_group(
    ax: plt.Axes,
    df: pd.DataFrame,
    group_col: str,
    title: str,
    max_groups: int = 6,
) -> None:
    groups = df[group_col].value_counts().head(max_groups).index.tolist()
    upper = df["duration_s"].quantile(0.999)
    lower = max(df["duration_s"].min(), 1e-3)
    bins = np.logspace(np.log10(lower), np.log10(max(upper, lower * 10)), 60)
    for group in groups:
        values = df.loc[df[group_col] == group, "duration_s"]
        ax.hist(values, bins=bins, histtype="step", density=True, linewidth=1.6, label=str(group))
    set_duration_ticks(ax)
    ax.set_yscale("log")
    ax.set_title(title)
    ax.set_ylabel("Density (log scale)")
    ax.legend(frameon=False, fontsize=8)


def plot_ecdf_by_group(
    ax: plt.Axes,
    df: pd.DataFrame,
    group_col: str,
    title: str,
    max_groups: int = 6,
) -> None:
    groups = df[group_col].value_counts().head(max_groups).index.tolist()
    for group in groups:
        values = np.sort(df.loc[df[group_col] == group, "duration_s"].to_numpy())
        y = np.arange(1, len(values) + 1) / len(values)
        ax.plot(values, y, linewidth=1.8, label=str(group))
    set_duration_ticks(ax)
    ax.set_title(title)
    ax.set_ylabel("ECDF")
    ax.set_ylim(0, 1.01)
    ax.legend(frameon=False, fontsize=8)


def plot_box_by_group(ax: plt.Axes, df: pd.DataFrame, group_col: str, title: str, max_groups: int = 8) -> None:
    groups = df[group_col].value_counts().head(max_groups).index.tolist()
    data = [df.loc[df[group_col] == group, "duration_s"].to_numpy() for group in groups]
    ax.boxplot(data, tick_labels=groups, showfliers=False)
    ax.set_yscale("log")
    ax.set_title(title)
    ax.set_ylabel("Duration")
    ax.set_yticks([1, 10, 60, 600, 3600, 6 * 3600, 24 * 3600, 7 * 24 * 3600])
    ax.set_yticklabels(["1s", "10s", "1m", "10m", "1h", "6h", "1d", "7d"])
    ax.grid(True, which="both", axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=25)


def make_plots(spot: pd.DataFrame, genai: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    plot_hist_by_group(axes[0, 0], spot, "job_type", "Spot-GPU job duration distribution")
    plot_ecdf_by_group(axes[0, 1], spot, "job_type", "Spot-GPU job duration ECDF")
    plot_hist_by_group(axes[1, 0], genai, "predict_type", "GenAI request execution-time distribution")
    plot_ecdf_by_group(axes[1, 1], genai, "predict_type", "GenAI request execution-time ECDF")
    fig.suptitle("Alibaba Cluster Trace 2026: AI Task Duration Distributions", fontsize=15)
    fig.savefig(OUT_DIR / "duration_distribution_overview.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), constrained_layout=True)
    plot_box_by_group(axes[0], spot, "job_type", "Spot-GPU duration by job type")
    plot_box_by_group(axes[1], spot, "gpu_model", "Spot-GPU duration by GPU model")
    fig.savefig(OUT_DIR / "spot_gpu_duration_boxplots.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), constrained_layout=True)
    plot_box_by_group(axes[0], genai, "predict_type", "GenAI duration by predict type")
    plot_box_by_group(axes[1], genai, "predict_status", "GenAI duration by status")
    fig.savefig(OUT_DIR / "genai_request_duration_boxplots.png", dpi=180)
    plt.close(fig)


def main() -> None:
    ensure_inputs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    spot = load_spot_jobs()
    genai = load_genai_requests()

    summaries = {
        "spot_gpu_by_job_type": duration_summary(spot, ["job_type"], "duration_s"),
        "spot_gpu_by_gpu_model": duration_summary(spot, ["gpu_model"], "duration_s"),
        "spot_gpu_by_job_type_gpu": duration_summary(spot, ["job_type", "gpu_model"], "duration_s"),
        "genai_by_predict_type": duration_summary(genai, ["predict_type"], "duration_s"),
        "genai_by_status": duration_summary(genai, ["predict_status"], "duration_s"),
        "genai_by_predict_type_status": duration_summary(
            genai, ["predict_type", "predict_status"], "duration_s"
        ),
    }

    for name, summary in summaries.items():
        summary.to_csv(OUT_DIR / f"{name}.csv", index=False)

    make_plots(spot, genai)

    print(f"spot_gpu valid jobs: {len(spot):,}")
    print(f"genai valid requests: {len(genai):,}")
    print("\nSpot-GPU by job_type:")
    print(summaries["spot_gpu_by_job_type"].to_string(index=False))
    print("\nGenAI by predict_type:")
    print(summaries["genai_by_predict_type"].to_string(index=False))
    print(f"\nOutputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
