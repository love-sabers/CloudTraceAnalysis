# P0 Agent Flow Trace Assets

Pulled from A800-dev workspace:

`/root/liujun/saber/project/CloudTrace`

Snapshot date: 2026-06-26

## Included

- `reports/`: P0 Markdown summaries and stage/resource SVG heatmaps.
- `processed/`: lightweight summary/status CSVs for Agent Reward Bench, Tau Bench, and OSWorld.
- `logs/`: batch/retry/rerun logs needed to audit OSWorld processing.
- `scripts/`: analysis and post-processing scripts used to generate the P0 results.

The repository root `scripts/` directory also contains the executable script copies for normal reuse.

## Excluded

Large raw or event-level data was intentionally not copied into GitHub:

- raw OSWorld zip archives, screenshots, videos, and temporary extraction trees
- event-level CSVs such as `*_events.csv`
- large per-run or raw trace dumps not needed for reproducing the reported summaries

Those files remain on A800-dev under the source workspace.

## OSWorld Final Scope

- 43 processed models
- 19,889 runs
- 2,250,210 events
- aggregate success rate: 0.333

Main OSWorld outputs:

- `reports/osworld_all_p0_summary.md`
- `reports/osworld_all_stage_resource_heatmap.svg`
- `processed/osworld_all_stage_resource_summary.csv`
- `processed/osworld_all_model_summary.csv`
- `processed/osworld_all_domain_summary.csv`

Merged P0 output:

- `reports/p0_agent_flow_resource_summary.md`
- `processed/p0_combined_stage_resource_summary.csv`
