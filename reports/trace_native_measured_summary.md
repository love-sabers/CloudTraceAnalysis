# Trace-Native Measured Resource Metrics

This report uses only quantities present in downloaded traces or mechanical byte/token counts derived from trace fields. It does not use proxy 0/1/2/3 resource levels.

## Inputs

- tau-bench / all: `/root/liujun/saber/project/CloudTrace/processed/tau_events.csv`
- AgentRewardBench / complete: `/root/liujun/saber/project/CloudTrace/processed/arb_events_complete.csv`
- OSWorld-Verified / all_models: `/root/liujun/saber/project/CloudTrace/processed/osworld_all_events.csv`

## Output Tables

- `processed/trace_native_run_stage_metrics.csv`: run-stage measured quantities.
- `processed/trace_native_stage_summary.csv`: source/scope/stage aggregate sums, p50, p95, max.
- `processed/trace_native_metric_coverage.csv`: which sources contain real elapsed-time fields.

## Coverage

|source|scope|run_stages|events|elapsed_coverage_ratio|
|---|---|---:|---:|---:|
|AgentRewardBench|assistantbench|1123|14158|0.000000|
|AgentRewardBench|visualwebarena|2564|29894|0.000000|
|AgentRewardBench|webarena|3391|33625|0.000000|
|AgentRewardBench|workarena|3939|65547|0.000000|
|OSWorld-Verified|UI-TARS-0717-100step|2889|56769|0.000000|
|OSWorld-Verified|UI-TARS-0717-15step|2889|21962|0.000000|
|OSWorld-Verified|autoglm_15steps|2955|17648|0.000000|
|OSWorld-Verified|autoglm_50steps|2958|37142|0.000000|
|OSWorld-Verified|claude-3-7-sonnet-20250219-100steps|2896|56185|0.000000|
|OSWorld-Verified|claude-3-7-sonnet-20250219-15steps|2890|23784|0.000000|
|OSWorld-Verified|claude-3-7-sonnet-20250219-50steps|2894|48530|0.000000|
|OSWorld-Verified|claude-4-sonnet-20250514-100steps|2895|51740|0.000000|
|OSWorld-Verified|claude-4-sonnet-20250514-15steps|2889|23655|0.000000|
|OSWorld-Verified|claude-4-sonnet-20250514-50steps|2893|44841|0.000000|
|OSWorld-Verified|claude-sonnet-4-5-20250929_100steps|2955|59197|0.000000|
|OSWorld-Verified|claude-sonnet-4-5-20250929_15steps|2914|25840|0.000000|
|OSWorld-Verified|claude-sonnet-4-5-20250929_50steps|2938|47094|0.000000|
|OSWorld-Verified|doubao-1-5-thinking-vision-pro-250428-100step|2889|64120|0.000000|
|OSWorld-Verified|doubao-1-5-thinking-vision-pro-250428-15step|2891|22273|0.000000|
|OSWorld-Verified|evocua_20260105|2939|52511|0.000000|
|OSWorld-Verified|evocua_8b_20260105|2953|57373|0.000000|
|OSWorld-Verified|jedi-7b-4o-100steps|2896|64904|0.000000|
|OSWorld-Verified|jedi-7b-4o-15steps|2893|20677|0.000000|
|OSWorld-Verified|jedi-7b-4o-50steps|2895|45787|0.000000|
|OSWorld-Verified|jedi-7b-o3-100steps|2899|49676|0.000000|
|OSWorld-Verified|jedi-7b-o3-15steps|2895|20815|0.000000|
|OSWorld-Verified|jedi-7b-o3-50steps|2897|44123|0.000000|
|OSWorld-Verified|kimi-k25|2940|49082|0.000000|
|OSWorld-Verified|kimi-k26|2925|46145|0.000000|
|OSWorld-Verified|kimi-vl-a3b-100step|2960|94354|0.000000|
|OSWorld-Verified|kimi-vl-a3b-15step|2921|24273|0.000000|
|OSWorld-Verified|mobile-agent-v3-gui-owl-7b|2899|21692|0.000000|
|OSWorld-Verified|mobileagent_v3|2889|47641|0.000000|
|OSWorld-Verified|o3_100steps|2961|96416|0.000000|
|OSWorld-Verified|o3_15steps|2959|25660|0.000000|
|OSWorld-Verified|o3_50steps|2964|71178|0.000000|
|OSWorld-Verified|o3_gta1_100steps|2953|55943|0.000000|
|OSWorld-Verified|o3_gta1_50steps|2955|43109|0.000000|
|OSWorld-Verified|opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-100steps|3028|134437|0.000000|
|OSWorld-Verified|opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-15steps|2994|63891|0.000000|
|OSWorld-Verified|opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-50steps|3009|110633|0.000000|
|OSWorld-Verified|opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-100steps|3018|128799|0.000000|
|OSWorld-Verified|opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-15steps|2980|65617|0.000000|
|OSWorld-Verified|opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-50steps|3017|112711|0.000000|
|OSWorld-Verified|opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-100step|2971|44666|0.000000|
|OSWorld-Verified|opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step|2935|22127|0.000000|
|OSWorld-Verified|opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-50step|2954|35190|0.000000|
|tau-bench|claude-3.5-sonnet::airline|2636|13309|0.000000|
|tau-bench|claude-3.5-sonnet::retail|6010|35094|0.000000|
|tau-bench|gpt-4o::airline|1213|6672|0.000000|
|tau-bench|gpt-4o::retail|2932|17782|0.000000|

## Notes

- `elapsed_sec` is emitted only when traces include elapsed fields. Missing time is left as zero with low coverage rather than estimated.
- `screenshot_bytes` is real byte size for OSWorld screenshots. AgentRewardBench currently exposes screenshot presence in processed events, not screenshot file bytes.
- Stage assignment is semantic, but each metric value is trace-native: token counts, byte counts, elapsed values, retry/error counts, and tool-call counts.
