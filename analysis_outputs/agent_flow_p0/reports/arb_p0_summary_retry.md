# AgentRewardBench P0 Summary (retry)
- Target trajectories: 289
- Processed trajectories: 289
- Failed trajectories: 0
- Events: 22646
- Events CSV: `/root/liujun/saber/project/CloudTrace/processed/arb_events_retry.csv`
- Runs CSV: `/root/liujun/saber/project/CloudTrace/processed/arb_runs_retry.csv`
- Stage summary: `/root/liujun/saber/project/CloudTrace/processed/arb_stage_resource_summary_retry.csv`
- Heatmap: `/root/liujun/saber/project/CloudTrace/reports/arb_stage_resource_heatmap_retry.svg`

## Benchmark Counts
- assistantbench: 42
- webarena: 247

## Interpretation
- This source represents web/GUI agent flows. Unlike tau-bench, browser/display and observation/context phases are first-class resource consumers.
- S2/S3 are observation and context-building phases driven by screenshots, accessibility trees, DOM-derived text, and browser state.
- S4 remains accelerator/HBM heavy due to per-step LLM/VLM decision making.
- S5/S6 capture browser actuation and page/environment wait, shifting demand toward CPU, network, and display/browser resources.
