#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REQ_CSV = ROOT / "data" / "genai_full" / "lora_request_trace.csv"
OUT_DIR = ROOT / "analysis_outputs" / "input_length_duration"


def load_requests() -> pd.DataFrame:
    cols = [
        "predict_type",
        "predict_status",
        "exec_time_seconds",
        "prompt_length",
        "negative_prompt_length",
        "num_images_per_prompt",
        "num_inference_steps",
        "num_lora",
    ]
    df = pd.read_csv(REQ_CSV, usecols=cols)
    numeric_cols = [
        "exec_time_seconds",
        "prompt_length",
        "negative_prompt_length",
        "num_images_per_prompt",
        "num_inference_steps",
        "num_lora",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["negative_prompt_length"] = df["negative_prompt_length"].fillna(0)
    df = df[
        df["exec_time_seconds"].notna()
        & (df["exec_time_seconds"] > 0)
        & df["prompt_length"].notna()
        & (df["prompt_length"] >= 0)
    ].copy()
    df["predict_type"] = df["predict_type"].fillna("UNKNOWN").astype(str)
    df["predict_status"] = df["predict_status"].fillna("UNKNOWN").astype(str)
    df["total_prompt_length"] = df["prompt_length"] + df["negative_prompt_length"]
    return df


def fit_stats(df: pd.DataFrame, x_col: str, y_col: str, group_col: str | None = None) -> pd.DataFrame:
    rows = []
    groups = [(None, df)] if group_col is None else list(df.groupby(group_col, dropna=False))
    for group, part in groups:
        part = part[[x_col, y_col]].replace([np.inf, -np.inf], np.nan).dropna()
        part = part[(part[x_col] > 0) & (part[y_col] > 0)]
        if len(part) < 3:
            continue

        x = part[x_col].to_numpy(dtype=float)
        y = part[y_col].to_numpy(dtype=float)

        pearson = float(np.corrcoef(x, y)[0, 1])
        spearman = float(pd.Series(x).corr(pd.Series(y), method="spearman"))

        linear_coef = np.polyfit(x, y, deg=1)
        linear_pred = np.polyval(linear_coef, x)
        linear_r2 = r2_score(y, linear_pred)

        lx = np.log10(x)
        ly = np.log10(y)
        log_coef = np.polyfit(lx, ly, deg=1)
        log_pred = np.polyval(log_coef, lx)
        log_r2 = r2_score(ly, log_pred)

        rows.append(
            {
                "group": "ALL" if group is None else group,
                "x_col": x_col,
                "count": len(part),
                "pearson": pearson,
                "spearman": spearman,
                "linear_slope": linear_coef[0],
                "linear_intercept": linear_coef[1],
                "linear_r2": linear_r2,
                "loglog_slope": log_coef[0],
                "loglog_intercept": log_coef[1],
                "loglog_r2": log_r2,
            }
        )
    return pd.DataFrame(rows)


def r2_score(y: np.ndarray, pred: np.ndarray) -> float:
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def plot_scatter(df: pd.DataFrame, stats: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)
    colors = {
        "TXT_2_IMG": "#1f77b4",
        "IMG_2_IMG": "#ff7f0e",
        "INPAINTING": "#2ca02c",
    }

    for ax, x_col, title in [
        (axes[0], "prompt_length", "Duration vs prompt length"),
        (axes[1], "total_prompt_length", "Duration vs prompt + negative prompt length"),
    ]:
        for predict_type, part in df.groupby("predict_type", dropna=False):
            ax.scatter(
                part[x_col],
                part["exec_time_seconds"],
                s=8,
                alpha=0.22,
                linewidths=0,
                label=str(predict_type),
                color=colors.get(str(predict_type)),
            )

        fit = stats[(stats["group"] == "ALL") & (stats["x_col"] == x_col)].iloc[0]
        x_min = max(float(df.loc[df[x_col] > 0, x_col].min()), 1e-6)
        x_max = float(df[x_col].max())
        x_line = np.linspace(x_min, x_max, 200)
        y_line = fit["linear_slope"] * x_line + fit["linear_intercept"]
        ax.plot(x_line, y_line, color="black", linewidth=1.8, label=f"linear R2={fit['linear_r2']:.3f}")

        ax.set_xlabel("Characters")
        ax.set_ylabel("Execution time (seconds)")
        ax.set_title(title)
        ax.grid(True, alpha=0.25)
        ax.legend(frameon=False, fontsize=8)

    fig.suptitle("Alibaba GenAI Trace: Input Length vs Execution Time", fontsize=15)
    fig.savefig(OUT_DIR / "input_length_vs_duration_scatter.png", dpi=180)
    plt.close(fig)


def plot_loglog(df: pd.DataFrame, stats: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)
    colors = {
        "TXT_2_IMG": "#1f77b4",
        "IMG_2_IMG": "#ff7f0e",
        "INPAINTING": "#2ca02c",
    }

    for ax, x_col, title in [
        (axes[0], "prompt_length", "Log-log: duration vs prompt length"),
        (axes[1], "total_prompt_length", "Log-log: duration vs total prompt length"),
    ]:
        plot_df = df[(df[x_col] > 0) & (df["exec_time_seconds"] > 0)]
        for predict_type, part in plot_df.groupby("predict_type", dropna=False):
            ax.scatter(
                part[x_col],
                part["exec_time_seconds"],
                s=8,
                alpha=0.22,
                linewidths=0,
                label=str(predict_type),
                color=colors.get(str(predict_type)),
            )

        fit = stats[(stats["group"] == "ALL") & (stats["x_col"] == x_col)].iloc[0]
        x_line = np.logspace(np.log10(plot_df[x_col].min()), np.log10(plot_df[x_col].max()), 200)
        y_line = 10 ** (fit["loglog_intercept"] + fit["loglog_slope"] * np.log10(x_line))
        ax.plot(x_line, y_line, color="black", linewidth=1.8, label=f"log-log R2={fit['loglog_r2']:.3f}")

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Characters (log scale)")
        ax.set_ylabel("Execution time, seconds (log scale)")
        ax.set_title(title)
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(frameon=False, fontsize=8)

    fig.suptitle("Alibaba GenAI Trace: Input Length vs Execution Time (Log-Log)", fontsize=15)
    fig.savefig(OUT_DIR / "input_length_vs_duration_loglog.png", dpi=180)
    plt.close(fig)


def main() -> None:
    if not REQ_CSV.exists():
        raise FileNotFoundError(REQ_CSV)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_requests()
    stats = pd.concat(
        [
            fit_stats(df, "prompt_length", "exec_time_seconds"),
            fit_stats(df, "total_prompt_length", "exec_time_seconds"),
            fit_stats(df, "prompt_length", "exec_time_seconds", "predict_type"),
            fit_stats(df, "total_prompt_length", "exec_time_seconds", "predict_type"),
        ],
        ignore_index=True,
    )
    stats.to_csv(OUT_DIR / "input_length_duration_fit_stats.csv", index=False)

    summary = (
        df.groupby("predict_type", dropna=False)
        .agg(
            requests=("exec_time_seconds", "count"),
            mean_prompt_length=("prompt_length", "mean"),
            p50_prompt_length=("prompt_length", "median"),
            p95_prompt_length=("prompt_length", lambda s: s.quantile(0.95)),
            mean_duration_s=("exec_time_seconds", "mean"),
            p50_duration_s=("exec_time_seconds", "median"),
            p95_duration_s=("exec_time_seconds", lambda s: s.quantile(0.95)),
        )
        .reset_index()
    )
    summary.to_csv(OUT_DIR / "input_length_duration_summary.csv", index=False)

    plot_scatter(df, stats)
    plot_loglog(df, stats)

    print(f"valid requests: {len(df):,}")
    print("\nSummary by predict_type:")
    print(summary.to_string(index=False))
    print("\nFit stats:")
    print(stats.to_string(index=False))
    print(f"\nOutputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
