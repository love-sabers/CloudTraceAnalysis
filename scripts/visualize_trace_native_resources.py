#!/usr/bin/env python3
"""Create visual summaries for trace-native agent-flow resource metrics."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RAW_METRICS = [
    "llm_input_tokens",
    "llm_output_tokens",
    "llm_total_tokens",
    "context_bytes",
    "screenshot_bytes",
    "action_bytes",
    "tool_arg_bytes",
    "runtime_log_bytes",
    "tool_call_count",
    "retry_count",
    "error_count",
    "event_count",
    "elapsed_sec",
]

RESOURCE_GROUPS = [
    ("llm_total_tokens", "LLM tokens", "tokens"),
    ("context_bytes", "Context bytes", "bytes"),
    ("screenshot_bytes", "Screenshot bytes", "bytes"),
    ("tool_payload_bytes", "Tool/action bytes", "bytes"),
    ("runtime_log_bytes", "Runtime log bytes", "bytes"),
    ("tool_call_count", "Tool calls", "count"),
    ("recovery_count", "Retry+error", "count"),
    ("event_count", "Trace events", "events"),
]


def p95(series: pd.Series) -> float:
    return float(series.quantile(0.95))


def stage_sort_key(stage_id: str) -> int:
    try:
        return int(str(stage_id).lstrip("S"))
    except ValueError:
        return 999


def human_number(value: float, unit: str) -> str:
    if not np.isfinite(value):
        return "n/a"
    if value == 0:
        return "0"
    if unit == "bytes":
        for suffix, factor in (("GiB", 1024**3), ("MiB", 1024**2), ("KiB", 1024)):
            if abs(value) >= factor:
                return f"{value / factor:.1f}{suffix}"
        return f"{value:.0f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    if value < 10 and value != int(value):
        return f"{value:.1f}"
    return f"{value:.0f}"


def load_metrics(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for metric in RAW_METRICS:
        if metric in df.columns:
            df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0.0)
    df["tool_payload_bytes"] = df.get("action_bytes", 0) + df.get("tool_arg_bytes", 0)
    df["recovery_count"] = df.get("retry_count", 0) + df.get("error_count", 0)
    return df


def build_stage_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metric_names = [name for name, _, _ in RESOURCE_GROUPS]
    grouped = df.groupby("stage_id", sort=False)
    for stage_id, group in grouped:
        stage_name = str(group["stage_name"].dropna().iloc[0])
        for metric in metric_names:
            values = group[metric].fillna(0.0)
            rows.append(
                {
                    "stage_id": stage_id,
                    "stage_name": stage_name,
                    "metric": metric,
                    "run_stage_count": int(len(values)),
                    "nonzero_ratio": float((values > 0).mean()) if len(values) else 0.0,
                    "sum": float(values.sum()),
                    "mean": float(values.mean()),
                    "p50": float(values.quantile(0.50)),
                    "p95": float(values.quantile(0.95)),
                    "max": float(values.max()),
                }
            )
    out = pd.DataFrame(rows)
    out["stage_sort"] = out["stage_id"].map(stage_sort_key)
    return out.sort_values(["stage_sort", "metric"]).drop(columns=["stage_sort"])


def build_source_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metric_names = [name for name, _, _ in RESOURCE_GROUPS]
    grouped = df.groupby(["source", "stage_id"], sort=False)
    for (source, stage_id), group in grouped:
        stage_name = str(group["stage_name"].dropna().iloc[0])
        for metric in metric_names:
            values = group[metric].fillna(0.0)
            rows.append(
                {
                    "source": source,
                    "stage_id": stage_id,
                    "stage_name": stage_name,
                    "metric": metric,
                    "run_stage_count": int(len(values)),
                    "nonzero_ratio": float((values > 0).mean()) if len(values) else 0.0,
                    "p50": float(values.quantile(0.50)),
                    "p95": float(values.quantile(0.95)),
                    "max": float(values.max()),
                }
            )
    out = pd.DataFrame(rows)
    out["stage_sort"] = out["stage_id"].map(stage_sort_key)
    return out.sort_values(["source", "stage_sort", "metric"]).drop(columns=["stage_sort"])


def normalized_pivot(profile: pd.DataFrame, value_col: str = "p95") -> pd.DataFrame:
    labels = {name: label for name, label, _ in RESOURCE_GROUPS}
    pivot = profile.pivot(index="stage_id", columns="metric", values=value_col)
    pivot = pivot[[name for name, _, _ in RESOURCE_GROUPS]]
    pivot.columns = [labels[col] for col in pivot.columns]
    pivot = pivot.reindex(sorted(pivot.index, key=stage_sort_key))
    logged = np.log1p(pivot.astype(float))
    denom = logged.max(axis=0).replace(0, 1)
    return logged.divide(denom, axis=1), pivot


def plot_heatmap(profile: pd.DataFrame, out_path: Path) -> None:
    norm, actual = normalized_pivot(profile, "p95")
    units = {label: unit for _, label, unit in RESOURCE_GROUPS}
    fig, ax = plt.subplots(figsize=(14, 7.8), constrained_layout=True)
    image = ax.imshow(norm.values, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(range(len(norm.columns)))
    ax.set_xticklabels(norm.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(norm.index)))
    ax.set_yticklabels(norm.index)
    ax.set_title("Stage resource demand heatmap (p95, column-normalized log scale)")
    ax.set_xlabel("Measured resource")
    ax.set_ylabel("Agent-flow stage")
    for y, stage in enumerate(norm.index):
        for x, label in enumerate(norm.columns):
            value = actual.loc[stage, label]
            text_color = "white" if norm.iloc[y, x] > 0.55 else "black"
            ax.text(
                x,
                y,
                human_number(value, units[label]),
                ha="center",
                va="center",
                fontsize=7,
                color=text_color,
            )
    cbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Relative demand within each resource")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_p50_p95_bars(profile: pd.DataFrame, out_path: Path) -> None:
    selected = [
        ("llm_total_tokens", "LLM tokens", "tokens"),
        ("context_bytes", "Context bytes", "bytes"),
        ("screenshot_bytes", "Screenshot bytes", "bytes"),
        ("tool_payload_bytes", "Tool/action bytes", "bytes"),
        ("tool_call_count", "Tool calls", "count"),
        ("event_count", "Trace events", "events"),
    ]
    stage_order = sorted(profile["stage_id"].unique(), key=stage_sort_key)
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5), constrained_layout=True)
    for ax, (metric, title, unit) in zip(axes.flat, selected):
        sub = (
            profile[profile["metric"] == metric]
            .set_index("stage_id")
            .reindex(stage_order)
            .fillna(0.0)
        )
        x = np.arange(len(stage_order))
        p50 = sub["p50"].values.astype(float)
        p95_values = sub["p95"].values.astype(float)
        if unit == "bytes":
            scale = 1024**2
            ylabel = "MiB"
        elif unit == "tokens" and np.nanmax(p95_values) >= 1000:
            scale = 1000
            ylabel = "K tokens"
        else:
            scale = 1
            ylabel = unit
        ax.bar(x - 0.18, p50 / scale, width=0.36, label="p50", color="#5B8DEF")
        ax.bar(x + 0.18, p95_values / scale, width=0.36, label="p95", color="#E56B6F")
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(stage_order)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)
    axes.flat[0].legend(loc="upper left", frameon=False)
    fig.suptitle("Measured demand amount and trace-time proxy by stage", fontsize=14)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_source_profiles(source_profile: pd.DataFrame, out_path: Path) -> None:
    sources = list(source_profile["source"].drop_duplicates())
    fig, axes = plt.subplots(
        1,
        len(sources),
        figsize=(5.8 * len(sources), 7.2),
        constrained_layout=True,
        squeeze=False,
    )
    labels = {name: label for name, label, _ in RESOURCE_GROUPS}
    for ax, source in zip(axes.flat, sources):
        sub = source_profile[source_profile["source"] == source]
        norm, _ = normalized_pivot(sub, "p95")
        image = ax.imshow(norm.values, aspect="auto", cmap="magma", vmin=0, vmax=1)
        ax.set_title(source)
        ax.set_xticks(range(len(norm.columns)))
        ax.set_xticklabels([labels.get(c, c) for c in norm.columns], rotation=45, ha="right")
        ax.set_yticks(range(len(norm.index)))
        ax.set_yticklabels(norm.index)
        ax.set_xlabel("Resource")
        ax.set_ylabel("Stage")
    cbar = fig.colorbar(image, ax=axes.ravel().tolist(), fraction=0.025, pad=0.02)
    cbar.set_label("Relative p95 demand within source/resource")
    fig.suptitle("Source-specific stage resource profiles", fontsize=14)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def plot_nonzero_presence(profile: pd.DataFrame, out_path: Path) -> None:
    pivot = profile.pivot(index="stage_id", columns="metric", values="nonzero_ratio")
    pivot = pivot[[name for name, _, _ in RESOURCE_GROUPS]]
    pivot.columns = [label for _, label, _ in RESOURCE_GROUPS]
    pivot = pivot.reindex(sorted(pivot.index, key=stage_sort_key))
    fig, ax = plt.subplots(figsize=(13.5, 6.8), constrained_layout=True)
    image = ax.imshow(pivot.values, aspect="auto", cmap="cividis", vmin=0, vmax=1)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("Resource presence ratio by stage")
    ax.set_xlabel("Measured resource")
    ax.set_ylabel("Agent-flow stage")
    for y in range(pivot.shape[0]):
        for x in range(pivot.shape[1]):
            val = pivot.iloc[y, x]
            color = "white" if val > 0.55 else "black"
            ax.text(x, y, f"{val:.0%}", ha="center", va="center", fontsize=8, color=color)
    cbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Fraction of run-stages with non-zero demand")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def write_report(
    profile: pd.DataFrame,
    source_profile: pd.DataFrame,
    figures: list[Path],
    out_path: Path,
) -> None:
    metric_units = {name: unit for name, _, unit in RESOURCE_GROUPS}
    metric_labels = {name: label for name, label, _ in RESOURCE_GROUPS}
    top_rows = []
    for metric, label, unit in RESOURCE_GROUPS:
        sub = profile[profile["metric"] == metric].copy()
        row = sub.sort_values("p95", ascending=False).iloc[0]
        top_rows.append(
            f"|{label}|{row.stage_id} {row.stage_name}|"
            f"{human_number(row.p95, unit)}|{row.nonzero_ratio:.0%}|"
        )

    source_rows = []
    for source in source_profile["source"].drop_duplicates():
        sub_source = source_profile[source_profile["source"] == source]
        for metric in ["llm_total_tokens", "context_bytes", "screenshot_bytes", "event_count"]:
            sub = sub_source[sub_source["metric"] == metric].sort_values("p95", ascending=False)
            if sub.empty:
                continue
            row = sub.iloc[0]
            source_rows.append(
                f"|{source}|{metric_labels[metric]}|{row.stage_id} {row.stage_name}|"
                f"{human_number(row.p95, metric_units[metric])}|"
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rel_figs = [Path("..") / fig for fig in figures]
    content = [
        "# Trace-Native Resource Visualizations",
        "",
        "These figures use only measured quantities in `processed/trace_native_run_stage_metrics.csv`.",
        "No 0/1/2/3 proxy resource levels are used.",
        "",
        "Time note: downloaded traces have zero wall-clock elapsed coverage, so the time view uses",
        "`event_count` as a trace-native discrete duration proxy. It should be read as stage length",
        "in recorded trace events, not seconds.",
        "",
        "Screenshot note: `screenshot_bytes` is a real image-byte footprint for OSWorld traces.",
        "For AgentRewardBench, the processed trace currently exposes screenshot presence/count-like",
        "values rather than full screenshot file bytes, so source-specific screenshot byte peaks",
        "should be interpreted through the coverage table.",
        "",
        "TerminalTraj note: TerminalTraj does not include provider-side token accounting.",
        "Its token values are byte-derived mechanical proxies; command bytes, terminal-output",
        "bytes, tool-call counts, and error/retry counts are direct trace-derived quantities.",
        "",
        "## Figures",
        "",
    ]
    for fig in rel_figs:
        content.append(f"- `{fig.as_posix()}`")
    content.extend(
        [
            "",
            "## Strongest Stage by Resource",
            "",
            "|resource|stage with highest p95|p95 demand|non-zero run-stage ratio|",
            "|---|---:|---:|---:|",
            *top_rows,
            "",
            "## Source-Specific Peaks",
            "",
            "|source|resource|stage with highest p95|p95 demand|",
            "|---|---|---:|---:|",
            *source_rows,
            "",
            "## Generated Tables",
            "",
            "- `processed/trace_native_visual_stage_profile.csv`",
            "- `processed/trace_native_visual_source_stage_profile.csv`",
            "",
        ]
    )
    out_path.write_text("\n".join(content), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="processed/trace_native_run_stage_metrics.csv",
        help="Run-stage measured metrics CSV.",
    )
    parser.add_argument("--processed-dir", default="processed")
    parser.add_argument("--figures-dir", default="figures")
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()

    input_path = Path(args.input)
    processed_dir = Path(args.processed_dir)
    figures_dir = Path(args.figures_dir)
    reports_dir = Path(args.reports_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = load_metrics(input_path)
    profile = build_stage_profile(df)
    source_profile = build_source_profile(df)

    profile_path = processed_dir / "trace_native_visual_stage_profile.csv"
    source_profile_path = processed_dir / "trace_native_visual_source_stage_profile.csv"
    profile.to_csv(profile_path, index=False)
    source_profile.to_csv(source_profile_path, index=False)

    figures = [
        figures_dir / "trace_native_stage_resource_heatmap.png",
        figures_dir / "trace_native_stage_resource_p50_p95.png",
        figures_dir / "trace_native_source_stage_profiles.png",
        figures_dir / "trace_native_source_stage_profiles_with_terminaltraj.png",
        figures_dir / "trace_native_stage_resource_presence.png",
    ]
    plot_heatmap(profile, figures[0])
    plot_p50_p95_bars(profile, figures[1])
    plot_source_profiles(source_profile, figures[2])
    plot_source_profiles(source_profile, figures[3])
    plot_nonzero_presence(profile, figures[4])
    write_report(profile, source_profile, figures, reports_dir / "trace_native_visual_summary.md")

    print(
        {
            "input": str(input_path),
            "stage_profile": str(profile_path),
            "source_stage_profile": str(source_profile_path),
            "figures": [str(path) for path in figures],
            "report": str(reports_dir / "trace_native_visual_summary.md"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
