# tau-bench P0 Agent Flow Trace Summary

## Dataset Snapshot

- Source commit: 59a200c6d575d595120f1cb70fea53cef0632f6b

- Raw files: 4 JSON files, about 50MB.

- Parsed runs: 1980

- Parsed events including synthetic tool-actuation and validation rows: 72857


## Run Summary by Model and Domain

|model|domain|runs|success_rate|avg_traj_messages|avg_tool_actuations|avg_error_recovery_events|
|---|---|---|---|---|---|---|
|claude-3.5-sonnet|airline|400|0.46|25.37|6.9|1.1|
|claude-3.5-sonnet|retail|920|0.692|29.44|7.7|1.36|
|gpt-4o|airline|200|0.42|26.54|5.82|0.47|
|gpt-4o|retail|460|0.604|30.54|7.12|0.97|


## Stage Resource Proxy Summary

|stage_id|stage_name|event_count|accelerator_gpu_npu|cpu|dram_hbm_memory|storage_io|network_io|browser_display_graphics|vm_container_isolation|
|---|---|---|---|---|---|---|---|---|---|
|S0|setup|0|0|0|0|0|0|0|0|
|S1|goal_interpretation_planning|1980|3.0|2.0|3.0|0.0|0.0|0.0|0.0|
|S2|observation_capture|14011|2.0|1.0|2.0|0.0|1.0|0.0|0.0|
|S3|context_building|0|0|0|0|0|0|0|0|
|S4|action_decision|25008|3.0|1.0|3.0|0.0|0.0|0.0|0.0|
|S5|actuation_tool_call|14285|0.0|2.0|1.0|1.0|3.0|0.0|0.0|
|S6|environment_result_wait|13362|0.003|2.0|2.001|1.001|3.0|0.0|0.0|
|S7|feedback_error_recovery|2231|3.0|2.0|3.0|1.0|2.0|0.0|0.0|
|S8|validation_finalization|1980|1.0|2.0|1.0|1.0|1.0|0.0|0.0|


## Interpretation

- tau-bench is a strict agent-flow source for tool/API conversational agents.

- The dominant phases alternate between accelerator/HBM-heavy LLM planning and decision stages (S1/S4), and network/API/CPU-heavy tool actuation/result stages (S5/S6).

- Browser/display and VM/container demand are near zero in this source; this makes tau-bench a useful contrast class against OSWorld and web/GUI agents.

- Error and recovery events (S7) are resource amplifiers because they re-enter the observe-decide-act loop.


## Artifacts

- `processed/tau_events.csv`: event-level normalized trace table.

- `processed/tau_runs.csv`: run-level counters.

- `processed/tau_run_summary.csv`: model/domain aggregate.

- `processed/tau_stage_resource_summary.csv`: stage-resource matrix.

- `reports/tau_stage_resource_heatmap.svg`: image-ready stage-resource heatmap.
