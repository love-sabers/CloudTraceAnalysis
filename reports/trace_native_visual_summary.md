# Trace-Native Resource Visualizations

These figures use only measured quantities in `processed/trace_native_run_stage_metrics.csv`.
No 0/1/2/3 proxy resource levels are used.

Time note: downloaded traces have zero wall-clock elapsed coverage, so the time view uses
`event_count` as a trace-native discrete duration proxy. It should be read as stage length
in recorded trace events, not seconds.

Screenshot note: `screenshot_bytes` is a real image-byte footprint for OSWorld traces.
For AgentRewardBench, the processed trace currently exposes screenshot presence/count-like
values rather than full screenshot file bytes, so source-specific screenshot byte peaks
should be interpreted through the coverage table.

TerminalTraj note: TerminalTraj does not include provider-side token accounting.
Its token values are byte-derived mechanical proxies; command bytes, terminal-output
bytes, tool-call counts, and error/retry counts are direct trace-derived quantities.

## Figures

- `../figures/trace_native_stage_resource_heatmap.png`
- `../figures/trace_native_stage_resource_p50_p95.png`
- `../figures/trace_native_source_stage_profiles.png`
- `../figures/trace_native_source_stage_profiles_with_terminaltraj.png`
- `../figures/trace_native_stage_resource_presence.png`

## Strongest Stage by Resource

|resource|stage with highest p95|p95 demand|non-zero run-stage ratio|
|---|---:|---:|---:|
|LLM tokens|S4 action_decision|43.7K|79%|
|Context bytes|S3 context_building|20.9MiB|100%|
|Screenshot bytes|S2 observation_capture|20.4MiB|43%|
|Tool/action bytes|S5 actuation_browser_gui|15.4KiB|100%|
|Runtime log bytes|S8 validation_finalization|144.7KiB|40%|
|Tool calls|S4 action_decision|31|57%|
|Retry+error|S7 feedback_error_recovery|20|100%|
|Trace events|S3 context_building|60|100%|

## Source-Specific Peaks

|source|resource|stage with highest p95|p95 demand|
|---|---|---:|---:|
|AgentRewardBench|LLM tokens|S4 action_decision|352.7K|
|AgentRewardBench|Context bytes|S2 observation_capture|1.2MiB|
|AgentRewardBench|Screenshot bytes|S2 observation_capture|31B|
|AgentRewardBench|Trace events|S2 observation_capture|31|
|OSWorld-Verified|LLM tokens|S4 action_decision|55.1K|
|OSWorld-Verified|Context bytes|S3 context_building|36.6MiB|
|OSWorld-Verified|Screenshot bytes|S2 observation_capture|36.6MiB|
|OSWorld-Verified|Trace events|S2 observation_capture|100|
|TerminalTraj|LLM tokens|S4 action_decision|6.4K|
|TerminalTraj|Context bytes|S2 observation_capture|40.3KiB|
|TerminalTraj|Screenshot bytes|S0 setup|0|
|TerminalTraj|Trace events|S1 goal_interpretation_planning|40|
|tau-bench|LLM tokens|S4 action_decision|2.0K|
|tau-bench|Context bytes|S6 environment_result_wait|12.1KiB|
|tau-bench|Screenshot bytes|S1 goal_interpretation_planning|0|
|tau-bench|Trace events|S4 action_decision|21|

## Generated Tables

- `processed/trace_native_visual_stage_profile.csv`
- `processed/trace_native_visual_source_stage_profile.csv`
