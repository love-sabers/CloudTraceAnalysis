#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import math
import urllib.request
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "kv_cache_traces"
OUT_DIR = ROOT / "analysis_outputs" / "kv_cache_traces"

MOONCAKE_URL = (
    "https://raw.githubusercontent.com/kvcache-ai/Mooncake/main/"
    "FAST25-release/arxiv-trace/mooncake_trace.jsonl"
)
MOONCAKE_PATH = DATA_DIR / "mooncake_trace.jsonl"
CC_PATH = DATA_DIR / "cc_traces_weka_042026.jsonl"

# HBM estimate defaults. They are intentionally explicit so the result is reproducible.
# Example class: Llama-3-70B style GQA KV cache, bf16/fp16 KV.
NUM_LAYERS = 80
NUM_KV_HEADS = 8
HEAD_DIM = 128
BYTES_PER_ELEM = 2
KV_BYTES_PER_TOKEN = 2 * NUM_LAYERS * NUM_KV_HEADS * HEAD_DIM * BYTES_PER_ELEM
CC_BLOCK_SIZE = 64
MOONCAKE_BLOCK_SIZE = 512


def ensure_mooncake() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if MOONCAKE_PATH.exists() and MOONCAKE_PATH.stat().st_size > 0:
        return
    print(f"Downloading Mooncake trace: {MOONCAKE_URL}")
    urllib.request.urlretrieve(MOONCAKE_URL, MOONCAKE_PATH)


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            try:
                parsed = ast.literal_eval(value)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
    return []


def load_mooncake() -> pd.DataFrame:
    ensure_mooncake()
    rows = []
    with MOONCAKE_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            input_len = first_present(obj, ["input_length", "input_len", "prompt_len", "in"])
            output_len = first_present(obj, ["output_length", "output_len", "out"])
            hash_ids = first_present(obj, ["hash_ids", "hash", "block_hash_ids"])
            rows.append(
                {
                    "dataset": "Mooncake/Kimi",
                    "trace_id": "mooncake_trace",
                    "arrival": first_present(obj, ["timestamp", "arrival_time", "time"]),
                    "input_tokens": to_float(input_len),
                    "output_tokens": to_float(output_len),
                    "hash_ids": as_list(hash_ids),
                }
            )
    df = pd.DataFrame(rows)
    return normalize_trace(df, MOONCAKE_BLOCK_SIZE)


def load_cc_traces() -> pd.DataFrame:
    if not CC_PATH.exists() or CC_PATH.stat().st_size == 0:
        raise FileNotFoundError(
            f"Missing CC trace file: {CC_PATH}. Download traces.jsonl from "
            "semianalysisai/cc-traces-weka-042026 first."
        )

    print("Loading CC Traces Weka from local JSONL...")
    rows = []
    with CC_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            trace = json.loads(line)
            trace_id = trace.get("id", f"trace_{len(rows)}")
            block_size = int(trace.get("block_size", CC_BLOCK_SIZE) or CC_BLOCK_SIZE)
            for i, req in enumerate(trace.get("requests", [])):
                rows.append(
                    {
                        "dataset": "CC Traces Weka",
                        "trace_id": trace_id,
                        "request_index": i,
                        "arrival": req.get("t", i),
                        "input_tokens": to_float(req.get("in")),
                        "output_tokens": to_float(req.get("out")),
                        "hash_ids": as_list(req.get("hash_ids")),
                        "block_size": block_size,
                        "model": req.get("model"),
                        "request_type": req.get("type"),
                    }
                )
    out = pd.DataFrame(rows)
    return normalize_trace(out, CC_BLOCK_SIZE)


def first_present(obj: dict, keys: Iterable[str]):
    for key in keys:
        if key in obj:
            return obj[key]
    return None


def to_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def choose_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_to_real = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower_to_real:
            return lower_to_real[candidate.lower()]
    return None


def normalize_trace(df: pd.DataFrame, block_size: int) -> pd.DataFrame:
    df = df.copy()
    if "trace_id" not in df.columns:
        df["trace_id"] = "trace"
    if "block_size" not in df.columns:
        df["block_size"] = block_size
    df["block_size"] = pd.to_numeric(df["block_size"], errors="coerce").fillna(block_size).astype("int64")
    df["input_tokens"] = pd.to_numeric(df["input_tokens"], errors="coerce")
    df["output_tokens"] = pd.to_numeric(df["output_tokens"], errors="coerce")
    df = df[df["input_tokens"].notna() & (df["input_tokens"] > 0)].copy()

    df["hash_ids"] = df["hash_ids"].map(as_list)
    df["kv_blocks_from_tokens"] = np.ceil(df["input_tokens"] / df["block_size"]).astype("int64")
    df["hash_block_count"] = df["hash_ids"].map(len).astype("int64")
    df["kv_blocks"] = df["hash_block_count"].where(df["hash_block_count"] > 0, df["kv_blocks_from_tokens"])
    df["kv_tokens_rounded"] = df["kv_blocks"] * df["block_size"]
    df["kv_hbm_gib"] = df["kv_tokens_rounded"] * KV_BYTES_PER_TOKEN / (1024**3)
    return df.reset_index(drop=True)


def add_prefix_reuse(df: pd.DataFrame) -> pd.DataFrame:
    seen: set = set()
    reuse_blocks = []
    miss_blocks = []
    reuse_ratios = []
    new_unique_blocks = []

    for hashes, block_count in zip(df["hash_ids"], df["kv_blocks"]):
        hashes = as_list(hashes)
        if hashes:
            reused = sum(1 for h in hashes if h in seen)
            for h in hashes:
                seen.add(h)
            blocks = len(hashes)
        else:
            reused = 0
            blocks = int(block_count)
        misses = max(blocks - reused, 0)
        reuse_blocks.append(reused)
        miss_blocks.append(misses)
        reuse_ratios.append(reused / blocks if blocks else 0.0)
        new_unique_blocks.append(len(seen))

    df = df.copy()
    df["prefix_reuse_blocks"] = reuse_blocks
    df["prefix_miss_blocks"] = miss_blocks
    df["prefix_reuse_ratio"] = reuse_ratios
    df["cumulative_unique_blocks"] = new_unique_blocks
    df["hbm_if_no_reuse_gib"] = df["kv_blocks"] * df["block_size"] * KV_BYTES_PER_TOKEN / (1024**3)
    df["hbm_new_blocks_gib"] = df["prefix_miss_blocks"] * df["block_size"] * KV_BYTES_PER_TOKEN / (1024**3)
    return df


def set_token_axis(ax: plt.Axes) -> None:
    ax.set_xscale("log")
    ax.set_xlabel("KV cache length proxy: input context tokens, rounded to 64-token blocks")
    ax.grid(True, which="both", alpha=0.25)


def set_hbm_axis(ax: plt.Axes) -> None:
    ax.set_xscale("log")
    ax.set_xlabel("Estimated request KV HBM footprint (GiB, log scale)")
    ax.grid(True, which="both", alpha=0.25)


def plot_kv_length_distribution(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for dataset, part in df.groupby("dataset"):
        values = part["kv_tokens_rounded"].clip(lower=1)
        bins = np.logspace(np.log10(values.min()), np.log10(values.max()), 70)
        ax.hist(values, bins=bins, histtype="step", density=True, linewidth=1.8, label=dataset)
    set_token_axis(ax)
    ax.set_yscale("log")
    ax.set_ylabel("Density (log scale)")
    ax.set_title("KV Cache Length Distribution")
    ax.legend(frameon=False)
    fig.savefig(OUT_DIR / "kv_cache_length_distribution.png", dpi=180)
    plt.close(fig)


def plot_prefix_reuse(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), constrained_layout=True)

    for dataset, part in df.groupby("dataset"):
        part = part.reset_index(drop=True)
        x = np.arange(1, len(part) + 1)
        window = max(50, min(1000, len(part) // 50))
        smoothed = part["prefix_reuse_ratio"].rolling(window, min_periods=1).mean()
        axes[0].plot(x, smoothed, linewidth=1.6, label=f"{dataset} ({window}-req rolling)")

        cum_total = part["kv_blocks"].cumsum()
        cum_new = part["prefix_miss_blocks"].cumsum()
        cum_reuse = 1.0 - (cum_new / cum_total.replace(0, np.nan))
        axes[1].plot(x, cum_reuse, linewidth=1.6, label=dataset)

    axes[0].set_title("Per-request prefix cache reuse ratio")
    axes[0].set_xlabel("Request order")
    axes[0].set_ylabel("Rolling mean reused block fraction")
    axes[0].set_ylim(-0.02, 1.02)
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(frameon=False)

    axes[1].set_title("Cumulative prefix cache reuse")
    axes[1].set_xlabel("Request order")
    axes[1].set_ylabel("1 - cumulative new blocks / cumulative requested blocks")
    axes[1].set_ylim(-0.02, 1.02)
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(frameon=False)

    fig.suptitle("Prefix Cache Reuse From Published Block Hash IDs", fontsize=14)
    fig.savefig(OUT_DIR / "prefix_cache_reuse.png", dpi=180)
    plt.close(fig)


def plot_hbm_pressure(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), constrained_layout=True)

    for dataset, part in df.groupby("dataset"):
        values = part["kv_hbm_gib"].clip(lower=1e-6)
        bins = np.logspace(np.log10(values.min()), np.log10(values.max()), 70)
        axes[0].hist(values, bins=bins, histtype="step", density=True, linewidth=1.8, label=dataset)

        ordered = part.reset_index(drop=True)
        x = np.arange(1, len(ordered) + 1)
        cum_no_reuse = ordered["hbm_if_no_reuse_gib"].cumsum()
        cum_new = ordered["hbm_new_blocks_gib"].cumsum()
        axes[1].plot(x, cum_no_reuse, linestyle="--", linewidth=1.2, label=f"{dataset} no reuse")
        axes[1].plot(x, cum_new, linewidth=1.8, label=f"{dataset} new blocks")

    set_hbm_axis(axes[0])
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Density (log scale)")
    axes[0].set_title("Per-request estimated KV HBM footprint")
    axes[0].legend(frameon=False)

    axes[1].set_yscale("log")
    axes[1].set_xlabel("Request order")
    axes[1].set_ylabel("Cumulative KV block traffic / residency proxy (GiB, log scale)")
    axes[1].set_title("HBM pressure proxy with and without prefix reuse")
    axes[1].grid(True, which="both", alpha=0.25)
    axes[1].legend(frameon=False, fontsize=8)

    fig.suptitle(
        "Estimated HBM Pressure From KV Cache Blocks "
        f"({KV_BYTES_PER_TOKEN / 1024**2:.2f} MiB/token assumption)",
        fontsize=13,
    )
    fig.savefig(OUT_DIR / "hbm_pressure_estimate.png", dpi=180)
    plt.close(fig)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.groupby("dataset")
        .agg(
            requests=("input_tokens", "count"),
            mean_input_tokens=("input_tokens", "mean"),
            p50_input_tokens=("input_tokens", "median"),
            p90_input_tokens=("input_tokens", lambda s: s.quantile(0.90)),
            p95_input_tokens=("input_tokens", lambda s: s.quantile(0.95)),
            p99_input_tokens=("input_tokens", lambda s: s.quantile(0.99)),
            mean_kv_hbm_gib=("kv_hbm_gib", "mean"),
            p50_kv_hbm_gib=("kv_hbm_gib", "median"),
            p95_kv_hbm_gib=("kv_hbm_gib", lambda s: s.quantile(0.95)),
            mean_prefix_reuse_ratio=("prefix_reuse_ratio", "mean"),
            total_kv_blocks=("kv_blocks", "sum"),
            total_new_blocks=("prefix_miss_blocks", "sum"),
        )
        .reset_index()
    )
    out["overall_prefix_reuse_ratio"] = 1 - out["total_new_blocks"] / out["total_kv_blocks"]
    return out


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mooncake = load_mooncake()
    cc = load_cc_traces()
    combined = pd.concat([mooncake, cc], ignore_index=True)

    # Preserve each dataset's own request order for prefix-cache simulation.
    reuse_parts = []
    for _, part in combined.groupby(["dataset", "trace_id"], sort=False):
        reuse_parts.append(add_prefix_reuse(part.reset_index(drop=True)))
    combined = pd.concat(reuse_parts, ignore_index=True)

    combined.to_parquet(OUT_DIR / "normalized_kv_cache_trace.parquet", index=False)
    summary = summarize(combined)
    summary.to_csv(OUT_DIR / "kv_cache_trace_summary.csv", index=False)

    plot_kv_length_distribution(combined)
    plot_prefix_reuse(combined)
    plot_hbm_pressure(combined)

    print(f"KV bytes per token assumption: {KV_BYTES_PER_TOKEN} bytes")
    print(f"KV MiB per token assumption: {KV_BYTES_PER_TOKEN / 1024**2:.4f}")
    print("\nSummary:")
    print(summary.to_string(index=False))
    print(f"\nOutputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
