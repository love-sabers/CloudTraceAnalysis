# Concurrency sweet-point analysis

This is an analytical decode-stage model, not an inference benchmark.

This variant intentionally disables HBM capacity constraints. It does not truncate by KV cache capacity and does not mark weight/KV residency as infeasible.

## Model

For each 72-GPU deployment and TP choice, `DP = 72 / TP`; MoE uses `EP = 72`.

Per-step latency is modeled as:

```text
step_latency = max(weight_read_time, compute_time, kv_read_time) + communication_overhead
node_decode_throughput = total_concurrency / step_latency
```

The scan variable is integer `batch_per_dp_group`. Total node concurrency is derived as `batch_per_dp_group * DP`.

Larger per-DP-group batch improves throughput by amortizing weight reads and increasing GEMM efficiency. The gains saturate when compute, KV bandwidth, or communication overhead dominates.

## Outputs

- `72gpu_concurrency_curves.csv.gz`: compressed full throughput curves
- `72gpu_concurrency_sweet_points.csv`: minimum per-DP-group batch and derived total concurrency for 90% and 95% peak throughput
- `72gpu_concurrency_sweet_point_ctx*_p90.png`: 90% sweet-point heatmaps for each context length
- `72gpu_concurrency_sweet_point_ctx*_p95.png`: 95% sweet-point heatmaps for each context length
- `72gpu_concurrency_throughput_curves.png`: normalized throughput curves for selected large MoE models

## Assumptions

- Context lengths for KV reads: `[8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576]` tokens
- Weights and KV cache use bf16/fp16.
- GPU performance assumptions are encoded in `GPU_PERF` in the script.
- MoE expert weight reads use an independent expert-activation approximation to capture diminishing weight-read amortization.

## Reproduce

```powershell
python scripts\analyze_concurrency_sweet_points.py --ignore-hbm-limit
```
