#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis_outputs" / "model_node_kv_thresholds"

BYTES_PER_GB = 1_000_000_000
WEIGHT_BYTES = 2
KV_BYTES = 2
USABLE_HBM_FRACTION = 0.90
GPU_COUNTS = [1, 2, 4, 8, 16, 36, 72]
MOE_TP_CANDIDATES = [16, 8, 4, 2, 1]


@dataclass(frozen=True)
class ModelSpec:
    name: str
    params_b: float
    layers: int
    kv_formula: str
    dense_params_b_explicit: float | None = None
    expert_params_b_explicit: float | None = None
    active_params_b: float | None = None
    num_experts: int | None = None
    experts_per_token: int | None = None
    kv_heads: int | None = None
    head_dim: int | None = None
    mla_kv_lora_rank: int | None = None
    mla_qk_rope_head_dim: int | None = None
    source: str = ""

    @property
    def weight_gb(self) -> float:
        return self.params_b * WEIGHT_BYTES

    @property
    def is_moe(self) -> bool:
        return self.expert_params_b_explicit is not None

    @property
    def expert_params_b(self) -> float:
        return self.expert_params_b_explicit or 0.0

    @property
    def dense_params_b(self) -> float:
        if not self.is_moe:
            return self.params_b
        if self.dense_params_b_explicit is not None:
            return self.dense_params_b_explicit
        return max(self.params_b - self.expert_params_b, 0.0)

    @property
    def kv_bytes_per_token(self) -> int:
        if self.kv_formula == "gqa":
            assert self.kv_heads is not None and self.head_dim is not None
            return 2 * self.layers * self.kv_heads * self.head_dim * KV_BYTES
        if self.kv_formula == "shared_kv":
            assert self.kv_heads is not None and self.head_dim is not None
            return self.layers * self.kv_heads * self.head_dim * KV_BYTES
        if self.kv_formula == "mla":
            assert self.mla_kv_lora_rank is not None and self.mla_qk_rope_head_dim is not None
            return self.layers * (self.mla_kv_lora_rank + self.mla_qk_rope_head_dim) * KV_BYTES
        raise ValueError(f"Unknown KV formula: {self.kv_formula}")

    @property
    def kv_mb_per_1k_tokens(self) -> float:
        return self.kv_bytes_per_token * 1000 / 1_000_000


@dataclass(frozen=True)
class GpuSpec:
    name: str
    hbm_gb: float
    source: str


MODELS = [
    ModelSpec(
        "Qwen3-30B-A3B",
        30.53191168,
        48,
        "gqa",
        dense_params_b_explicit=1.540882432,
        expert_params_b_explicit=28.991029248,
        active_params_b=3.3,
        num_experts=128,
        experts_per_token=8,
        kv_heads=4,
        head_dim=128,
        source="Qwen3-30B-A3B public Hugging Face config/model card",
    ),
    ModelSpec(
        "Qwen3-32B",
        32.8,
        64,
        "gqa",
        kv_heads=8,
        head_dim=80,
        source="Qwen3-32B public Hugging Face config/model card",
    ),
    ModelSpec(
        "Llama-3.3-70B",
        70.6,
        80,
        "gqa",
        kv_heads=8,
        head_dim=128,
        source="Meta Llama 3.3 70B public Hugging Face config/model card",
    ),
    ModelSpec(
        "Qwen3-235B-A22B",
        235.092836352,
        94,
        "gqa",
        dense_params_b_explicit=7.996440576,
        expert_params_b_explicit=227.096395776,
        active_params_b=22.0,
        num_experts=128,
        experts_per_token=8,
        kv_heads=4,
        head_dim=128,
        source="Qwen3-235B-A22B public Hugging Face config/model card",
    ),
    ModelSpec(
        "GLM-4.5-355B-A32B",
        355.0,
        92,
        "gqa",
        dense_params_b_explicit=7.7116288,
        expert_params_b_explicit=347.2883712,
        active_params_b=32.0,
        num_experts=128,
        experts_per_token=8,
        kv_heads=8,
        head_dim=128,
        source="Z.ai GLM-4.5 public Hugging Face config/model card",
    ),
    ModelSpec(
        "Llama-3.1-405B",
        405.0,
        126,
        "gqa",
        kv_heads=8,
        head_dim=128,
        source="Meta Llama 3.1 405B public Hugging Face config/model card",
    ),
    ModelSpec(
        "Qwen3-Coder-480B-A35B",
        480.15409152,
        62,
        "gqa",
        dense_params_b_explicit=12.06976512,
        expert_params_b_explicit=468.0843264,
        active_params_b=35.0,
        num_experts=160,
        experts_per_token=8,
        kv_heads=8,
        head_dim=128,
        source="Qwen3-Coder-480B-A35B public Hugging Face config/model card",
    ),
    ModelSpec(
        "DeepSeek-V3/R1-671B",
        671.025522688,
        61,
        "mla",
        dense_params_b_explicit=17.116751872,
        expert_params_b_explicit=653.908770816,
        active_params_b=37.0,
        num_experts=256,
        experts_per_token=8,
        mla_kv_lora_rank=512,
        mla_qk_rope_head_dim=64,
        source="DeepSeek-V3/R1 public config, optimized MLA KV cache layout",
    ),
    ModelSpec(
        "Kimi-K2-1T-A32B",
        1026.407327744,
        61,
        "mla",
        dense_params_b_explicit=11.721304064,
        expert_params_b_explicit=1014.68602368,
        active_params_b=32.0,
        num_experts=384,
        experts_per_token=8,
        mla_kv_lora_rank=512,
        mla_qk_rope_head_dim=64,
        source="Moonshot Kimi-K2 public config/model card, optimized MLA KV cache layout",
    ),
    ModelSpec(
        "DeepSeek-V4-Flash-284B",
        284.0,
        43,
        "shared_kv",
        dense_params_b_explicit=6.974609408,
        expert_params_b_explicit=277.025390592,
        active_params_b=35.0,
        num_experts=128,
        experts_per_token=8,
        kv_heads=1,
        head_dim=512,
        source="DeepSeek-V4-Flash public config/model card, shared KV cache layout",
    ),
    ModelSpec(
        "DeepSeek-V4-Pro-1.6T",
        1600.0,
        43,
        "shared_kv",
        dense_params_b_explicit=52.603813888,
        expert_params_b_explicit=1547.396186112,
        active_params_b=64.0,
        num_experts=512,
        experts_per_token=8,
        kv_heads=1,
        head_dim=512,
        source="DeepSeek-V4-Pro public config/model card, shared KV cache layout",
    ),
]

GPUS = [
    GpuSpec("A100", 80, "NVIDIA A100 80GB public product specifications"),
    GpuSpec("H100NVL", 94, "NVIDIA H100 NVL 94GB public product specifications"),
    GpuSpec("B200", 186, "NVIDIA B200 186GB public product specifications"),
]


def deployment_specs() -> list[dict]:
    rows = []
    for gpu in GPUS:
        for count in GPU_COUNTS:
            rows.append(
                {
                    "deployment": f"{gpu.name}x{count}",
                    "gpu_model": gpu.name,
                    "gpus_per_node": count,
                    "hbm_gb_per_gpu": gpu.hbm_gb,
                    "node_hbm_gb": gpu.hbm_gb * count,
                    "usable_hbm_gb": gpu.hbm_gb * count * USABLE_HBM_FRACTION,
                    "node_source": gpu.source,
                }
            )
    return rows


def divisors(value: int) -> list[int]:
    return [candidate for candidate in range(1, value + 1) if value % candidate == 0]


def candidate_parallel_plans(model: ModelSpec, gpu_count: int) -> list[dict]:
    plans = []
    tp_candidates = [tp for tp in [1, 2, 4, 8, 16, 32, 36, 72] if tp <= gpu_count]
    for tp_size in tp_candidates:
        if gpu_count % tp_size != 0:
            continue
        dp_size = gpu_count // tp_size
        ep_size = gpu_count if model.is_moe else 1
        plans.append(
            {
                "tp_size": tp_size,
                "dp_size": dp_size,
                "ep_size": ep_size,
                "kv_replication_factor": 1,
                "parallelism": f"TP{tp_size}/DP{dp_size}/EP{ep_size}",
            }
        )
    return plans


def evaluate_plan(model: ModelSpec, dep: dict, plan: dict) -> dict:
    tp_size = plan["tp_size"]
    dp_size = plan["dp_size"]
    ep_size = plan["ep_size"]

    dense_weight_gb = model.dense_params_b * WEIGHT_BYTES
    expert_weight_gb = model.expert_params_b * WEIGHT_BYTES

    # Normal serving layout: TP * DP = GPU count. Dense/shared weights are
    # replicated by DP and sharded by TP. MoE expert weights are sharded by EP;
    # for large expert-parallel serving, EP is modeled as the whole GPU set.
    resident_weight_gb = dense_weight_gb * dp_size + expert_weight_gb
    weight_per_gpu_gb = dense_weight_gb / tp_size + expert_weight_gb / ep_size
    usable_per_gpu_gb = dep["hbm_gb_per_gpu"] * USABLE_HBM_FRACTION
    residual_total_gb = dep["usable_hbm_gb"] - resident_weight_gb
    residual_per_gpu_gb = usable_per_gpu_gb - weight_per_gpu_gb
    feasible = residual_total_gb > 0 and residual_per_gpu_gb > 0
    kv_bytes_per_token_per_gpu = model.kv_bytes_per_token / tp_size
    kv_bytes_per_resident_token = model.kv_bytes_per_token * plan["kv_replication_factor"]
    max_kv_tokens = residual_total_gb * BYTES_PER_GB / kv_bytes_per_resident_token if feasible else 0.0
    max_kv_tokens_per_gpu = residual_per_gpu_gb * BYTES_PER_GB / kv_bytes_per_token_per_gpu if feasible else 0.0

    return {
        "tp_size": tp_size,
        "dp_size": dp_size,
        "ep_size": ep_size,
        "parallelism": plan["parallelism"],
        "kv_replication_factor": plan["kv_replication_factor"],
        "dense_params_b_est": model.dense_params_b,
        "expert_params_b_est": model.expert_params_b,
        "resident_weight_gb_bf16": resident_weight_gb,
        "weight_gb_per_gpu_after_tp_ep": weight_per_gpu_gb,
        "residual_hbm_gb_for_kv": max(residual_total_gb, 0.0),
        "residual_hbm_gb_for_kv_per_gpu": max(residual_per_gpu_gb, 0.0),
        "kv_bytes_per_token_per_gpu_bf16": kv_bytes_per_token_per_gpu,
        "max_resident_kv_tokens": int(max_kv_tokens),
        "max_resident_kv_tokens_per_gpu": int(max_kv_tokens_per_gpu),
        "max_resident_kv_tokens_per_dp_replica": int(max_kv_tokens / dp_size) if dp_size else 0,
        "max_resident_kv_k_tokens": max_kv_tokens / 1_000,
        "feasible_after_tp_dp_ep_weights": feasible,
    }


def choose_plan(model: ModelSpec, dep: dict, policy: str) -> dict:
    evaluated = [evaluate_plan(model, dep, plan) for plan in candidate_parallel_plans(model, dep["gpus_per_node"])]
    feasible = [plan for plan in evaluated if plan["feasible_after_tp_dp_ep_weights"]]
    if feasible:
        if policy == "capacity_opt":
            return max(feasible, key=lambda item: item["max_resident_kv_tokens_per_gpu"])
        if policy == "dp_max":
            return max(feasible, key=lambda item: (item["dp_size"], item["max_resident_kv_tokens"]))
        raise ValueError(f"Unknown policy: {policy}")
    return max(evaluated, key=lambda item: item["residual_hbm_gb_for_kv"]) if evaluated else {}


def estimate_thresholds() -> pd.DataFrame:
    rows = []
    for dep in deployment_specs():
        for model in MODELS:
            for policy in ["capacity_opt", "dp_max"]:
                plan = choose_plan(model, dep, policy)
                rows.append(
                    {
                        **dep,
                        **plan,
                        "policy": policy,
                        "model": model.name,
                        "params_b": model.params_b,
                        "active_params_b": model.active_params_b,
                        "num_experts": model.num_experts,
                        "experts_per_token": model.experts_per_token,
                        "dense_params_b_config": model.dense_params_b,
                        "expert_params_b_config": model.expert_params_b,
                        "weight_gb_bf16": model.weight_gb,
                        "layers": model.layers,
                        "kv_formula": model.kv_formula,
                        "kv_heads": model.kv_heads,
                        "head_dim": model.head_dim,
                        "mla_kv_lora_rank": model.mla_kv_lora_rank,
                        "mla_qk_rope_head_dim": model.mla_qk_rope_head_dim,
                        "kv_bytes_per_token_bf16": model.kv_bytes_per_token,
                        "kv_mb_per_1k_tokens_bf16": model.kv_mb_per_1k_tokens,
                        "model_source": model.source,
                    }
                )
    return pd.DataFrame(rows)


def format_tokens(value: float, feasible: bool) -> str:
    if not feasible:
        return "weights\nOOM"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value / 1_000:.0f}K"


def plot_threshold_heatmap(df: pd.DataFrame, policy: str) -> None:
    df = df[df["policy"] == policy].copy()
    model_order = [m.name for m in MODELS]
    dep_order = [f"{gpu.name}x{count}" for gpu in GPUS for count in GPU_COUNTS]

    pivot = df.pivot(index="model", columns="deployment", values="max_resident_kv_tokens_per_gpu").loc[model_order, dep_order]
    feasible = df.pivot(index="model", columns="deployment", values="feasible_after_tp_dp_ep_weights").loc[model_order, dep_order]
    plan = df.pivot(index="model", columns="deployment", values="parallelism").loc[model_order, dep_order]

    values = pivot.to_numpy(dtype=float)
    color_values = np.full_like(values, np.nan, dtype=float)
    positive = values > 0
    color_values[positive] = np.log10(values[positive])

    fig, ax = plt.subplots(figsize=(30, 12), constrained_layout=True)
    cmap = plt.cm.viridis.copy()
    cmap.set_bad("#d9d9d9")
    im = ax.imshow(color_values, cmap=cmap, aspect="auto")

    ax.set_xticks(np.arange(len(dep_order)))
    ax.set_xticklabels(dep_order, rotation=35, ha="right")
    ax.set_yticks(np.arange(len(model_order)))
    ax.set_yticklabels(model_order)
    ax.set_title("Single-GPU resident KV length before per-card HBM capacity is exhausted")
    ax.set_xlabel("Deployment shape")
    ax.set_ylabel("Open large model")

    for i, model in enumerate(model_order):
        for j, dep in enumerate(dep_order):
            token_value = pivot.loc[model, dep]
            is_feasible = bool(feasible.loc[model, dep])
            token_label = format_tokens(token_value, is_feasible)
            label = f"{token_label}\n{plan.loc[model, dep]}" if is_feasible else token_label
            ax.text(
                j,
                i,
                label,
                ha="center",
                va="center",
                color="#555555",
                fontsize=9,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white", alpha=0.75)] if is_feasible else None,
            )

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("log10(max resident KV tokens per GPU)")

    subtitle = (
        f"Policy: {policy}. Cell value is per-GPU KV token capacity. Assumptions: bf16/fp16 weights and KV cache, TP*DP=GPU count, "
        "MoE uses EP=GPU count; "
        f"{USABLE_HBM_FRACTION:.0%} of nominal node HBM usable for weights+KV; "
        "DP replicates dense/shared weights and EP shards expert weights."
    )
    fig.text(0.5, -0.02, subtitle, ha="center", va="top", fontsize=9)
    fig.savefig(OUT_DIR / f"model_node_max_kv_tokens_heatmap_{policy}.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def plot_72_node_tp_sweep(df: pd.DataFrame) -> None:
    model_order = [m.name for m in MODELS]
    tp_order = [1, 2, 4, 8, 12, 18, 24, 36, 72]

    rows = []
    for gpu in GPUS:
        dep = {
            "deployment": f"{gpu.name}x72",
            "gpu_model": gpu.name,
            "gpus_per_node": 72,
            "hbm_gb_per_gpu": gpu.hbm_gb,
            "node_hbm_gb": gpu.hbm_gb * 72,
            "usable_hbm_gb": gpu.hbm_gb * 72 * USABLE_HBM_FRACTION,
            "node_source": gpu.source,
        }
        for model in MODELS:
            for tp_size in tp_order:
                if 72 % tp_size != 0:
                    continue
                plan = {
                    "tp_size": tp_size,
                    "dp_size": 72 // tp_size,
                    "ep_size": 72 if model.is_moe else 1,
                    "kv_replication_factor": 1,
                    "parallelism": f"TP{tp_size}/DP{72 // tp_size}/EP{72 if model.is_moe else 1}",
                }
                result = evaluate_plan(model, dep, plan)
                rows.append(
                    {
                        "gpu_model": gpu.name,
                        "tp_size": tp_size,
                        "model": model.name,
                        **result,
                    }
                )

    sweep = pd.DataFrame(rows)
    sweep.to_csv(OUT_DIR / "model_node_72gpu_tp_sweep.csv", index=False)

    fig, axes = plt.subplots(1, len(GPUS), figsize=(26, 10), sharey=True, constrained_layout=True)
    for ax, gpu in zip(axes, GPUS):
        part = sweep[sweep["gpu_model"] == gpu.name]
        pivot = part.pivot(index="model", columns="tp_size", values="max_resident_kv_tokens_per_gpu").loc[
            model_order, tp_order
        ]
        feasible = part.pivot(index="model", columns="tp_size", values="feasible_after_tp_dp_ep_weights").loc[
            model_order, tp_order
        ]
        plan = part.pivot(index="model", columns="tp_size", values="parallelism").loc[model_order, tp_order]

        values = pivot.to_numpy(dtype=float)
        color_values = np.full_like(values, np.nan, dtype=float)
        positive = values > 0
        color_values[positive] = np.log10(values[positive])

        cmap = plt.cm.viridis.copy()
        cmap.set_bad("#d9d9d9")
        im = ax.imshow(color_values, cmap=cmap, aspect="auto")
        ax.set_title(f"{gpu.name}x72")
        ax.set_xlabel("TP size")
        ax.set_xticks(np.arange(len(tp_order)))
        ax.set_xticklabels([str(tp) for tp in tp_order], rotation=0)
        ax.set_yticks(np.arange(len(model_order)))
        ax.set_yticklabels(model_order)

        for i, model in enumerate(model_order):
            for j, tp_size in enumerate(tp_order):
                is_feasible = bool(feasible.loc[model, tp_size])
                token_label = format_tokens(pivot.loc[model, tp_size], is_feasible)
                label = f"{token_label}\n{plan.loc[model, tp_size]}" if is_feasible else token_label
                ax.text(
                    j,
                    i,
                    label,
                    ha="center",
                    va="center",
                    color="#555555",
                    fontsize=7.2,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white", alpha=0.75)] if is_feasible else None,
                )

    axes[0].set_ylabel("Open large model")
    cbar = fig.colorbar(im, ax=axes.ravel().tolist())
    cbar.set_label("log10(max resident KV tokens per GPU)")
    fig.suptitle("72-GPU Node TP Sweep: Single-GPU KV Capacity Under TP/DP Tradeoff", fontsize=16)
    fig.text(
        0.5,
        -0.01,
        "Assumptions: TP*DP=72; MoE EP=72; cell value is per-GPU KV token capacity after per-card weight residency.",
        ha="center",
        va="top",
        fontsize=10,
    )
    fig.savefig(OUT_DIR / "model_node_72gpu_tp_sweep_heatmap.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def write_assumptions(threshold_df: pd.DataFrame) -> None:
    lines = [
        "# Model-node KV cache HBM thresholds",
        "",
        "This is a theoretical capacity analysis. It does not run inference or trigger OOM.",
        "",
        "## Deployment model",
        "",
        "- Horizontal axis uses deployment shapes such as `A100x1`, `A100x2`, `H100NVLx8`, `B200x8`.",
        "- Deployment uses `TP * DP = GPU count`.",
        "- `capacity_opt` chooses the feasible TP/DP plan with the largest per-GPU resident KV capacity.",
        "- `dp_max` chooses the feasible TP/DP plan with the largest DP degree, then breaks ties by KV capacity.",
        "- Dense model weights are sharded by TP and replicated by DP.",
        "- MoE dense/shared and routed expert parameter counts are config-derived explicit values, not inferred from active-parameter counts.",
        "- MoE dense/shared weights are sharded by TP and replicated by DP.",
        "- MoE routed expert weights use `EP = GPU count` and are sharded across the whole deployment.",
        "- Heatmap cells are normalized per GPU: each card's remaining HBM divided by that card's TP-sharded KV bytes/token.",
        "- Aggregate and per-DP-replica KV capacities are still emitted in the CSV for reference.",
        "- MoE model weights are treated as resident HBM weights; active-parameter count is not used for memory capacity.",
        "",
        "## Formula",
        "",
        "```text",
        "usable_hbm = gpu_count * hbm_per_gpu * 0.90",
        "weight_hbm = total_model_params * 2 bytes",
        "standard_gqa_kv_bytes_per_token = 2 * layers * kv_heads * head_dim * 2 bytes",
        "mla_kv_bytes_per_token = layers * (kv_lora_rank + qk_rope_head_dim) * 2 bytes",
        "shared_kv_bytes_per_token = layers * kv_heads * head_dim * 2 bytes",
        "dense/shared_params and routed_expert_params are computed from public model configs",
        "dense_resident_weight_hbm = dense/shared_weight * DP",
        "moe_resident_weight_hbm = dense/shared_weight * DP + routed_expert_weight",
        "residual_hbm_per_gpu = usable_hbm_per_gpu - weight_hbm_per_gpu",
        "kv_bytes_per_token_per_gpu = kv_bytes_per_token / TP",
        "max_resident_kv_tokens_per_gpu = residual_hbm_per_gpu / kv_bytes_per_token_per_gpu",
        "max_resident_kv_tokens = (usable_hbm - resident_weight_hbm) / kv_bytes_per_token",
        "max_resident_kv_tokens_per_dp_replica = max_resident_kv_tokens / DP",
        "```",
        "",
        "## Outputs",
        "",
        "- `model_node_kv_thresholds.csv`: full threshold table",
        "- `model_node_max_kv_tokens_heatmap_capacity_opt.png`: capacity-oriented per-GPU threshold heatmap with selected TP/DP/EP labels",
        "- `model_node_max_kv_tokens_heatmap_dp_max.png`: DP-concurrency-oriented per-GPU threshold heatmap with selected TP/DP/EP labels",
        "- `model_node_72gpu_tp_sweep_heatmap.png`: 72-GPU TP sweep heatmap",
        "- `model_node_72gpu_tp_sweep.csv`: full 72-GPU TP sweep table",
        "",
        "## Notes",
        "",
        "- `Qwen3.5` was not included because no public open-source model/config with that name was found.",
        "- DeepSeek-V4 rows use the public V4-style shared-KV configuration when available.",
        "",
        "## Sources recorded in the CSV",
        "",
    ]
    for source in sorted(set(threshold_df["model_source"]).union(set(threshold_df["node_source"]))):
        lines.append(f"- {source}")

    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    thresholds = estimate_thresholds()
    thresholds.to_csv(OUT_DIR / "model_node_kv_thresholds.csv", index=False)
    for policy in ["capacity_opt", "dp_max"]:
        plot_threshold_heatmap(thresholds, policy)
    plot_72_node_tp_sweep(thresholds)
    write_assumptions(thresholds)

    cols = ["policy", "model", "deployment", "parallelism", "max_resident_kv_tokens_per_gpu", "max_resident_kv_tokens", "feasible_after_tp_dp_ep_weights"]
    print(thresholds[cols].to_string(index=False))
    print(f"\nOutputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
