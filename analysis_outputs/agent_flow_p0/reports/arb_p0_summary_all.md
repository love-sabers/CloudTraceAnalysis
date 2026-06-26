# AgentRewardBench P0 Summary (all)
- Target trajectories: 1302
- Processed trajectories: 1013
- Failed trajectories: 289
- Events: 120578
- Events CSV: `/root/liujun/saber/project/CloudTrace/processed/arb_events_all.csv`
- Runs CSV: `/root/liujun/saber/project/CloudTrace/processed/arb_runs_all.csv`
- Stage summary: `/root/liujun/saber/project/CloudTrace/processed/arb_stage_resource_summary_all.csv`
- Heatmap: `/root/liujun/saber/project/CloudTrace/reports/arb_stage_resource_heatmap_all.svg`

## Benchmark Counts
- assistantbench: 90
- visualwebarena: 300
- webarena: 151
- workarena: 472

## Interpretation
- This source represents web/GUI agent flows. Unlike tau-bench, browser/display and observation/context phases are first-class resource consumers.
- S2/S3 are observation and context-building phases driven by screenshots, accessibility trees, DOM-derived text, and browser state.
- S4 remains accelerator/HBM heavy due to per-step LLM/VLM decision making.
- S5/S6 capture browser actuation and page/environment wait, shifting demand toward CPU, network, and display/browser resources.
