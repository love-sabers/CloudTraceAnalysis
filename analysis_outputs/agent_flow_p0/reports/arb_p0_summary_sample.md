# AgentRewardBench P0 Summary (sample)
- Target trajectories: 4
- Processed trajectories: 4
- Failed trajectories: 0
- Events: 521
- Events CSV: `/root/liujun/saber/project/CloudTrace/processed/arb_events_sample.csv`
- Runs CSV: `/root/liujun/saber/project/CloudTrace/processed/arb_runs_sample.csv`
- Stage summary: `/root/liujun/saber/project/CloudTrace/processed/arb_stage_resource_summary_sample.csv`
- Heatmap: `/root/liujun/saber/project/CloudTrace/reports/arb_stage_resource_heatmap_sample.svg`

## Benchmark Counts
- assistantbench: 1
- visualwebarena: 1
- webarena: 1
- workarena: 1

## Interpretation
- This source represents web/GUI agent flows. Unlike tau-bench, browser/display and observation/context phases are first-class resource consumers.
- S2/S3 are observation and context-building phases driven by screenshots, accessibility trees, DOM-derived text, and browser state.
- S4 remains accelerator/HBM heavy due to per-step LLM/VLM decision making.
- S5/S6 capture browser actuation and page/environment wait, shifting demand toward CPU, network, and display/browser resources.
