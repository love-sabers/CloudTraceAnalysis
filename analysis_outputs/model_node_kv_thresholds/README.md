# Model-node KV cache HBM thresholds

This is a theoretical capacity analysis. It does not run inference or trigger OOM.

## Deployment model

- Horizontal axis uses deployment shapes such as `A100x1`, `A100x2`, `H100NVLx8`, `B200x8`.
- Deployment uses `TP * DP = GPU count`.
- `capacity_opt` chooses the feasible TP/DP plan with the largest per-GPU resident KV capacity.
- `dp_max` chooses the feasible TP/DP plan with the largest DP degree, then breaks ties by KV capacity.
- Dense model weights are sharded by TP and replicated by DP.
- MoE dense/shared and routed expert parameter counts are config-derived explicit values, not inferred from active-parameter counts.
- MoE dense/shared weights are sharded by TP and replicated by DP.
- MoE routed expert weights use `EP = GPU count` and are sharded across the whole deployment.
- Heatmap cells are normalized per GPU: each card's remaining HBM divided by that card's TP-sharded KV bytes/token.
- Aggregate and per-DP-replica KV capacities are still emitted in the CSV for reference.
- MoE model weights are treated as resident HBM weights; active-parameter count is not used for memory capacity.

## Formula

```text
usable_hbm = gpu_count * hbm_per_gpu * 0.90
weight_hbm = total_model_params * 2 bytes
standard_gqa_kv_bytes_per_token = 2 * layers * kv_heads * head_dim * 2 bytes
mla_kv_bytes_per_token = layers * (kv_lora_rank + qk_rope_head_dim) * 2 bytes
shared_kv_bytes_per_token = layers * kv_heads * head_dim * 2 bytes
dense/shared_params and routed_expert_params are computed from public model configs
dense_resident_weight_hbm = dense/shared_weight * DP
moe_resident_weight_hbm = dense/shared_weight * DP + routed_expert_weight
residual_hbm_per_gpu = usable_hbm_per_gpu - weight_hbm_per_gpu
kv_bytes_per_token_per_gpu = kv_bytes_per_token / TP
max_resident_kv_tokens_per_gpu = residual_hbm_per_gpu / kv_bytes_per_token_per_gpu
max_resident_kv_tokens = (usable_hbm - resident_weight_hbm) / kv_bytes_per_token
max_resident_kv_tokens_per_dp_replica = max_resident_kv_tokens / DP
```

## Outputs

- `model_node_kv_thresholds.csv`: full threshold table
- `model_node_max_kv_tokens_heatmap_capacity_opt.png`: capacity-oriented per-GPU threshold heatmap with selected TP/DP/EP labels
- `model_node_max_kv_tokens_heatmap_dp_max.png`: DP-concurrency-oriented per-GPU threshold heatmap with selected TP/DP/EP labels
- `model_node_72gpu_tp_sweep_heatmap.png`: 72-GPU TP sweep heatmap
- `model_node_72gpu_tp_sweep.csv`: full 72-GPU TP sweep table

## Notes

- `Qwen3.5` was not included because no public open-source model/config with that name was found.
- DeepSeek-V4 rows use the public V4-style shared-KV configuration when available.

## Sources recorded in the CSV

- DeepSeek-V3/R1 public config, optimized MLA KV cache layout
- DeepSeek-V4-Flash public config/model card, shared KV cache layout
- DeepSeek-V4-Pro public config/model card, shared KV cache layout
- Meta Llama 3.1 405B public Hugging Face config/model card
- Meta Llama 3.3 70B public Hugging Face config/model card
- Moonshot Kimi-K2 public config/model card, optimized MLA KV cache layout
- NVIDIA A100 80GB public product specifications
- NVIDIA B200 186GB public product specifications
- NVIDIA H100 NVL 94GB public product specifications
- Qwen3-235B-A22B public Hugging Face config/model card
- Qwen3-30B-A3B public Hugging Face config/model card
- Qwen3-32B public Hugging Face config/model card
- Qwen3-Coder-480B-A35B public Hugging Face config/model card
- Z.ai GLM-4.5 public Hugging Face config/model card
