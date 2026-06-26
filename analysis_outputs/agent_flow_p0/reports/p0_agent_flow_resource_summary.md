# P0 Agent Flow Hardware-Resource Summary

## Sources Processed

- tau-bench: 1980 runs, 72857 events.
- AgentRewardBench: 1302 runs, 143224 events.
- OSWorld-Verified all processed models: 19889 runs, 2250210 events.

## AgentRewardBench Complete Run Summary

|benchmark|runs|successful|unsuccessful|avg_steps|avg_input_tokens|avg_output_tokens|avg_error_steps|
|---|---|---|---|---|---|---|---|
|assistantbench|132|10|122|19.99|107981.04|2105.84|4.23|
|visualwebarena|300|91|209|18.91|140315.03|2248.94|2.06|
|webarena|398|146|252|15.88|92803.07|1776.7|2.03|
|workarena|472|108|364|26.83|200653.48|3500.18|1.62|

## Cross-Source Interpretation

- tau-bench represents tool/API-heavy agent flow: S1/S4 are accelerator/HBM dominated, while S5/S6 shift to CPU/network/API service demand; browser/display demand is effectively absent.
- AgentRewardBench represents web/GUI agent flow: S2/S3/S5/S6 introduce sustained browser/display, CPU, memory, and network demand around each LLM decision.
- OSWorld-Verified represents desktop/GUI/VM agent flow: S0/S5/S6/S8 add strong VM/container, display, CPU, and storage demand around real app execution and validation.
- Across both sources, the flow alternates between accelerator-bound reasoning and environment-bound execution; this supports stage-aware rather than whole-flow-static resource allocation.
- S7 feedback/error recovery is a resource amplifier: it re-enters observe/context/decide/act loops and causes repeated accelerator plus environment demand.

## Artifacts

- `/root/liujun/saber/project/CloudTrace/processed/tau_events.csv`
- `/root/liujun/saber/project/CloudTrace/processed/arb_events_complete.csv`
- `/root/liujun/saber/project/CloudTrace/processed/p0_combined_stage_resource_summary.csv`
- `/root/liujun/saber/project/CloudTrace/reports/tau_stage_resource_heatmap.svg`
- `/root/liujun/saber/project/CloudTrace/reports/arb_stage_resource_heatmap_complete.svg`
- `/root/liujun/saber/project/CloudTrace/processed/osworld_all_stage_resource_summary.csv`
