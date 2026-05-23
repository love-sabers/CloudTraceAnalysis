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
OUT_DIR = ROOT / "analysis_outputs" / "duration_resource_relation"


def load_jobs() -> pd.DataFrame:
    cols = [
        "job_name",
        "organization",
        "gpu_model",
        "cpu_request",
        "gpu_request",
        "worker_num",
        "submit_time",
        "duration",
        "job_type",
    ]
    df = pd.read_csv(SPOT_JOB_CSV, usecols=cols)
    for col in ["cpu_request", "gpu_request", "worker_num", "duration"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[
        df["duration"].notna()
        & (df["duration"] > 0)
        & df["gpu_request"].notna()
        & df["cpu_request"].notna()
        & df["worker_num"].notna()
        & (df["gpu_request"] > 0)
        & (df["cpu_request"] > 0)
        & (df["worker_num"] > 0)
    ].copy()

    df["job_type"] = df["job_type"].fillna("UNKNOWN").astype(str)
    df["gpu_model"] = df["gpu_model"].fillna("UNKNOWN").astype(str)
    df["total_gpu_requested"] = df["gpu_request"] * df["worker_num"]
    df["total_cpu_requested"] = df["cpu_request"] * df["worker_num"]
    df["duration_h"] = df["duration"] / 3600.0
    return df


def sample_for_scatter(df: pd.DataFrame, max_points_per_type: int = 80_000) -> pd.DataFrame:
    parts = []
    for _, group in df.groupby("job_type", dropna=False):
        if len(group) > max_points_per_type:
            parts.append(group.sample(max_points_per_type, random_state=42))
        else:
            parts.append(group)
    return pd.concat(parts, ignore_index=True)


def add_duration_axis(ax: plt.Axes) -> None:
    ax.set_yscale("log")
    ax.set_yticks([1, 10, 60, 600, 3600, 6 * 3600, 24 * 3600, 7 * 24 * 3600])
    ax.set_yticklabels(["1s", "10s", "1m", "10m", "1h", "6h", "1d", "7d"])
    ax.grid(True, which="both", alpha=0.25)


def plot_scatter(sample: pd.DataFrame) -> None:
    colors = {"HP": "#1f77b4", "Spot": "#ff7f0e"}
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)

    for job_type, group in sample.groupby("job_type", dropna=False):
        color = colors.get(str(job_type), None)
        axes[0].scatter(
            group["total_gpu_requested"],
            group["duration"],
            s=5,
            alpha=0.12,
            linewidths=0,
            label=str(job_type),
            color=color,
        )
        axes[1].scatter(
            group["total_cpu_requested"],
            group["duration"],
            s=5,
            alpha=0.12,
            linewidths=0,
            label=str(job_type),
            color=color,
        )

    axes[0].set_xscale("log")
    axes[0].set_xlabel("Total GPUs requested = gpu_request * worker_num (log scale)")
    axes[0].set_ylabel("Job duration")
    axes[0].set_title("Duration vs total GPU request")
    add_duration_axis(axes[0])
    axes[0].legend(frameon=False)

    axes[1].set_xscale("log")
    axes[1].set_xlabel("Total CPUs requested = cpu_request * worker_num (log scale)")
    axes[1].set_ylabel("Job duration")
    axes[1].set_title("Duration vs total CPU request")
    add_duration_axis(axes[1])
    axes[1].legend(frameon=False)

    fig.suptitle("Alibaba Spot-GPU Trace: Task Duration vs Requested Resource Size", fontsize=15)
    fig.savefig(OUT_DIR / "duration_vs_resource_scatter.png", dpi=180)
    plt.close(fig)


def plot_gpu_detail(sample: pd.DataFrame) -> None:
    gpu_models = sample["gpu_model"].value_counts().head(6).index.tolist()
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), sharex=True, sharey=True, constrained_layout=True)
    axes_flat = axes.ravel()

    for ax, gpu_model in zip(axes_flat, gpu_models):
        g = sample[sample["gpu_model"] == gpu_model]
        for job_type, part in g.groupby("job_type", dropna=False):
            ax.scatter(
                part["total_gpu_requested"],
                part["duration"],
                s=5,
                alpha=0.13,
                linewidths=0,
                label=str(job_type),
            )
        ax.set_xscale("log")
        add_duration_axis(ax)
        ax.set_title(str(gpu_model))
        ax.set_xlabel("Total GPUs requested")
        ax.set_ylabel("Duration")

    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", frameon=False)
    fig.suptitle("Duration vs Total GPU Request by GPU Model", fontsize=15)
    fig.savefig(OUT_DIR / "duration_vs_gpu_request_by_model.png", dpi=180)
    plt.close(fig)


def make_summary(df: pd.DataFrame) -> pd.DataFrame:
    bins = [0, 1, 2, 4, 8, 16, 32, 64, 128, np.inf]
    labels = ["<=1", "2", "3-4", "5-8", "9-16", "17-32", "33-64", "65-128", ">128"]
    df = df.copy()
    df["gpu_request_bucket"] = pd.cut(
        df["total_gpu_requested"], bins=bins, labels=labels, right=True, include_lowest=True
    )
    summary = (
        df.groupby(["job_type", "gpu_request_bucket"], observed=False)
        .agg(
            jobs=("job_name", "count"),
            mean_duration_s=("duration", "mean"),
            p50_duration_s=("duration", "median"),
            p90_duration_s=("duration", lambda s: s.quantile(0.90)),
            p95_duration_s=("duration", lambda s: s.quantile(0.95)),
            p99_duration_s=("duration", lambda s: s.quantile(0.99)),
            mean_total_cpu=("total_cpu_requested", "mean"),
        )
        .reset_index()
    )
    for col in ["mean_duration_s", "p50_duration_s", "p90_duration_s", "p95_duration_s", "p99_duration_s"]:
        summary[col.replace("_s", "_h")] = summary[col] / 3600.0
    return summary


def main() -> None:
    if not SPOT_JOB_CSV.exists():
        raise FileNotFoundError(SPOT_JOB_CSV)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = load_jobs()
    sample = sample_for_scatter(jobs)
    summary = make_summary(jobs)
    summary.to_csv(OUT_DIR / "duration_by_gpu_request_bucket.csv", index=False)

    plot_scatter(sample)
    plot_gpu_detail(sample)

    corr = jobs[["duration", "total_gpu_requested", "total_cpu_requested", "worker_num"]].corr(
        method="spearman"
    )
    corr.to_csv(OUT_DIR / "spearman_correlation.csv")

    print(f"valid jobs: {len(jobs):,}")
    print(f"scatter sample: {len(sample):,}")
    print("\nSpearman correlation:")
    print(corr.to_string())
    print("\nDuration by total GPU request bucket:")
    print(summary.to_string(index=False))
    print(f"\nOutputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
