# CloudTraceAnalysis

CloudTraceAnalysis contains trace-driven and theory-first analyses for cloud LLM
serving. The current archive focuses on two questions:

- how much KV cache can fit under realistic model, GPU, TP, DP, and EP choices;
- how much decode concurrency is needed before throughput reaches its practical
  saturation point.

The analyses are intended for design-space exploration rather than inference
benchmarking. Most recent work uses public model/GPU parameters plus Alibaba
cloud trace data where available.

## Repository Layout

- `scripts/`: reproducible Python analysis and plotting scripts.
- `analysis_outputs/model_node_kv_thresholds/`: HBM/KV capacity thresholds for
  large open models across A100, H100NVL, and B200 nodes from 1 to 72 GPUs.
- `analysis_outputs/concurrency_sweet_points/`: 72-GPU decode concurrency
  sweet-point analysis with HBM capacity limits enabled.
- `analysis_outputs/concurrency_sweet_points_no_hbm_limit/`: the same
  concurrency analysis with HBM capacity limits intentionally disabled.
- `analysis_outputs/decode_weight_kv_theory/`: theoretical decode-stage
  weight-read, KV-read, prefill-recompute, and long/short-context resource
  figures.
- `analysis_outputs/duration_distribution/`,
  `analysis_outputs/duration_resource_relation/`,
  `analysis_outputs/input_length_duration/`, and
  `analysis_outputs/kv_cache_traces/`: earlier trace-derived exploratory
  figures.
- `AlibabaTrace.md`: notes on the Alibaba trace fields and analysis context.

## Current Modeling Conventions

Model-node HBM capacity uses BF16/FP16 weights and KV cache. Dense/shared
weights are replicated by DP and sharded by TP. MoE expert weights are sharded
over EP, with large MoE serving modeled as `EP = GPU count`. Normal node
deployment follows `TP * DP = GPU count`.

The maintained GPU memory assumptions are:

- A100: 80 GB HBM per GPU
- H100NVL: 94 GB HBM per GPU
- B200: 186 GB HBM per GPU

Concurrency analysis is restricted to 72-GPU nodes. It scans integer
`batch_per_dp_group` values, derives total node concurrency as
`batch_per_dp_group * DP`, and reports the minimum per-DP-group batch that
reaches 90% or 95% of each curve's peak decode throughput. Heatmap cells include
`B` for per-DP-group batch, `C` for total concurrency, and the selected
`TP/DP/EP` placement.

## Reproducing Outputs

Run from the repository root:

```powershell
python scripts\analyze_model_node_kv_thresholds.py
python scripts\analyze_concurrency_sweet_points.py
python scripts\analyze_concurrency_sweet_points.py --ignore-hbm-limit
python scripts\plot_decode_weight_kv_theory.py
python scripts\plot_kv_read_vs_prefill_threshold.py
python scripts\plot_deepseek_v4_kv_read_vs_prefill_threshold.py
python scripts\plot_long_vs_short_context_resources.py
```

The first concurrency command regenerates the HBM-constrained variant. The
second regenerates the no-HBM-limit variant for isolating the pure throughput
scaling model.

## Figure Inventory

Every archived PNG has been reviewed for the necessary reading information:
title or facet label, axis labels, units where applicable, colorbar/legend, and
cell annotations for deployment heatmaps. Generated review contact sheets and
Python bytecode caches are intentionally ignored and should not be archived.

The largest archived data artifact is
`analysis_outputs/concurrency_sweet_points_no_hbm_limit/72gpu_concurrency_curves.csv.gz`,
which stores the full no-HBM-limit curve scan in compressed form.
