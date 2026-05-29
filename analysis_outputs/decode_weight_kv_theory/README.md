# Decode weight-vs-KV theory dataset

Prepared on 2026-05-23 for a theory-first analysis of decode-stage memory
pressure. This package does not contain local machine measurements.

## Files

- `model_configs.csv`: public model architecture fields needed to estimate
  weight reads, KV reads, and attention arithmetic intensity.
- `theory_baseline_b1_fp16.csv`: batch=1, FP16/BF16 weight and KV theoretical
  bytes by context length.
- `sensitivity_crossover.csv`: crossover context length sensitivity for batch,
  weight quantization, and KV quantization.
- `public_trace_facts.csv`: public profiling/benchmark facts that can calibrate
  the theory model. These are secondary observations, not measurements from this
  workspace.
- `gpu_assumptions.csv`: GPU peak bandwidth assumptions for roofline-style
  first-pass estimates.
- `source_catalog.csv`: source URLs and intended use.
- `roofline_estimates.csv`: derived KV memory time and attention compute time
  used by the roofline plot.
- `large_model_configs.csv`: large-model and MoE architecture fields reused
  from `analysis_outputs/model_node_kv_thresholds`.
- `large_model_weight_kv_theory.csv`: large-model theoretical KV/weight traffic
  by context length.
- `large_model_524k_summary.csv`: large-model summary at 524,288 context.
- `kv_read_vs_prefill_threshold_by_tp_assumptions.csv`: model, TP, bandwidth,
  and NVIDIA compute assumptions for the KV-read versus prefill-recompute
  context threshold.
- `kv_read_vs_prefill_threshold_by_tp_grid.csv`: enumerated TP, bandwidth, and
  GPU compute grid with the resulting context-length threshold.
- `kv_read_vs_prefill_threshold_by_tp_summary.csv`: min/max threshold summary
  for each TP and GPU compute point.
- `deepseek_v4_kv_read_vs_prefill_threshold_by_tp_assumptions.csv`: DeepSeek-V4
  Flash/Pro model and hardware assumptions for the same threshold analysis.
- `deepseek_v4_kv_read_vs_prefill_threshold_by_tp_grid.csv`: DeepSeek-V4
  Flash/Pro TP, bandwidth, and GPU compute grid.
- `deepseek_v4_kv_read_vs_prefill_threshold_by_tp_summary.csv`: DeepSeek-V4
  min/max threshold summary for each TP and GPU compute point.
- `long_vs_short_context_resource_assumptions.csv`: model, hardware, scenario,
  and formula assumptions for multi-turn long-context versus short-context
  resource curves.
- `long_vs_short_context_resource_curves.csv`: simulated resource curve samples
  over inference time.
- `long_vs_short_context_resource_summary.csv`: peak and final resource summary
  for each scenario.

## Generated figures

- `fig1_weight_vs_kv_bytes.png`: theoretical weight reads and KV reads by
  context length.
- `fig2_kv_weight_ratio.png`: KV/weight read ratio by context length.
- `fig3_attention_arithmetic_intensity.png`: attention arithmetic intensity by
  model, derived from Q heads / KV heads.
- `fig4_roofline_kv_memory_vs_attention_compute.png`: roofline-style estimate
  of KV HBM time versus QK/AV compute time.
- `fig5_large_model_kv_active_weight_ratio.png`: large-model KV/active-weight
  ratio, with 524k context marked.
- `fig6_large_model_crossover_contexts.png`: active-weight and total-resident
  weight crossover contexts for large dense/MoE models.
- `fig7_kv_read_vs_prefill_threshold_by_tp_heatmap.png`: heatmap of the
  context-length threshold where reading an existing sharded KV cache becomes
  faster than recomputing it through prefill, faceted by TP.
- `fig8_deepseek_v4_kv_read_vs_prefill_threshold_by_tp_heatmap.png`: same
  threshold heatmap for DeepSeek-V4-Flash and DeepSeek-V4-Pro.
- `fig9_long_vs_short_context_resource_curves.png`: theoretical compute,
  resident KV capacity, and memory-bandwidth curves over inference time for
  multi-turn ultra-long context and few-turn short context scenarios.

## Core formulas

```text
weight_read_bytes_per_output_token ~= params * weight_dtype_bytes / batch
kv_read_bytes_per_output_token ~= layers * context_len * 2 * n_kv_heads * head_dim * kv_dtype_bytes
crossover_context ~= weight_read_bytes_per_output_token / (layers * 2 * n_kv_heads * head_dim * kv_dtype_bytes)
attention_FLOPs ~= 4 * layers * context_len * n_q_heads * head_dim
attention_AI ~= attention_FLOPs / kv_read_bytes
             ~= 2 * n_q_heads / (n_kv_heads * kv_dtype_bytes)
```

For FP16/BF16 KV, `attention_AI ~= n_q_heads / n_kv_heads`. This is the first
theoretical handle for whether KV reads may overlap with QK/AV compute.

## Important limitations

- `weight_read_bytes` assumes weights are streamed from HBM once per generated
  token and are amortized by batch. Real kernels may see different reuse through
  L2/cache residency and scheduling.
- `kv_read_bytes` counts logical K and V cache traffic. Paged KV layouts,
  prefix-cache reuse, quantized KV, and Flash/PagedAttention implementations can
  change effective HBM traffic.
- Public trace facts are heterogeneous: they use different GPUs, models,
  kernels, sequence lengths, and serving stacks. Use them for priors and sanity
  checks, not direct apples-to-apples comparison.
- A800 bandwidth should be verified on the target server with `nvidia-smi -q` or
  vendor-specific specs before final roofline numbers are reported.
