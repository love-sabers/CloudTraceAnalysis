# OSWorld-Verified P0 Summary (All Processed Models)

- Models processed: 43
- Runs: 19889
- Events: 2250210
- Success rate: 0.333

## Model Summary

|model|runs|events|successes|success_rate|avg_steps|
|---|---|---|---|---|---|
|UI-TARS-0717-100step|361|56769|140|0.388|30.83|
|UI-TARS-0717-15step|361|21962|113|0.313|11.56|
|autoglm_15steps|361|17648|161|0.446|9.01|
|autoglm_50steps|361|37142|163|0.452|19.48|
|claude-3-7-sonnet-20250219-100steps|361|56185|124|0.343|30.5|
|claude-3-7-sonnet-20250219-15steps|361|23784|95|0.263|12.57|
|claude-3-7-sonnet-20250219-50steps|361|48530|125|0.346|26.28|
|claude-4-sonnet-20250514-100steps|361|51740|143|0.396|28.06|
|claude-4-sonnet-20250514-15steps|361|23655|110|0.305|12.5|
|claude-4-sonnet-20250514-50steps|361|44841|151|0.418|24.23|
|claude-sonnet-4-5-20250929_100steps|361|59197|217|0.601|32.05|
|claude-sonnet-4-5-20250929_15steps|361|25840|151|0.418|13.69|
|claude-sonnet-4-5-20250929_50steps|361|47094|203|0.562|25.4|
|doubao-1-5-thinking-vision-pro-250428-100step|361|64120|118|0.327|34.92|
|doubao-1-5-thinking-vision-pro-250428-15step|361|22273|95|0.263|11.74|
|evocua_20260105|361|52511|199|0.551|28.35|
|evocua_8b_20260105|361|57373|161|0.446|30.89|
|jedi-7b-4o-100steps|361|64904|104|0.288|35.26|
|jedi-7b-4o-15steps|361|20677|93|0.258|10.84|
|jedi-7b-4o-50steps|361|45787|93|0.258|24.73|
|jedi-7b-o3-100steps|361|49676|179|0.496|26.86|
|jedi-7b-o3-15steps|361|20815|150|0.416|10.92|
|jedi-7b-o3-50steps|361|44123|175|0.485|23.81|
|kimi-k25|359|49082|222|0.618|26.6|
|kimi-k26|358|46145|252|0.704|25.02|
|kimi-vl-a3b-100step|361|94354|35|0.097|51.0|
|kimi-vl-a3b-15step|361|24273|34|0.094|12.78|
|mobile-agent-v3-gui-owl-7b|361|21692|113|0.313|11.39|
|mobileagent_v3|361|47641|135|0.374|25.77|
|o3_100steps|369|96416|80|0.217|51.59|
|o3_15steps|369|25660|32|0.087|13.29|
|o3_50steps|369|71178|60|0.163|37.93|
|o3_gta1_100steps|369|55943|182|0.493|29.72|
|o3_gta1_50steps|369|43109|167|0.453|22.76|
|opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-100steps|1083|134437|365|0.337|23.94|
|opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-15steps|1083|63891|309|0.285|11.11|
|opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-50steps|1083|110633|358|0.331|19.61|
|opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-100steps|1083|128799|278|0.257|22.98|
|opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-15steps|1083|65617|254|0.235|11.42|
|opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-50steps|1082|112711|292|0.27|20.05|
|opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-100step|361|44666|61|0.169|23.8|
|opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-15step|361|22127|58|0.161|11.57|
|opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-50step|361|35190|69|0.191|18.73|

## Domain Summary

|domain|runs|successes|success_rate|avg_steps|
|---|---|---|---|---|
|chrome|2526|1008|0.399|19.52|
|gimp|1430|771|0.539|17.13|
|libreoffice_calc|2584|612|0.237|25.58|
|libreoffice_impress|2585|840|0.325|18.88|
|libreoffice_writer|1265|485|0.383|19.16|
|multi_apps|5155|851|0.165|28.5|
|os|1320|626|0.474|14.67|
|thunderbird|825|441|0.535|19.61|
|vlc|935|292|0.312|17.75|
|vs_code|1264|693|0.548|18.71|

## Resource Interpretation

- S0/S5/S6/S8 are consistently environment-bound: VM/container isolation, display/graphics, CPU, and storage demand are high because OSWorld exercises real desktop apps and validation.
- S1/S3/S4 are reasoning/context-bound: accelerator and HBM demand stay high around prompt construction and action synthesis.
- OSWorld therefore exposes heterogeneous demand inside one flow: model-serving phases alternate with desktop-environment phases, and S7 loops amplify both sides when recovery is needed.

## Artifacts

- `/root/liujun/saber/project/CloudTrace/processed/osworld_all_events.csv`
- `/root/liujun/saber/project/CloudTrace/processed/osworld_all_runs.csv`
- `/root/liujun/saber/project/CloudTrace/processed/osworld_all_stage_resource_summary.csv`
- `/root/liujun/saber/project/CloudTrace/processed/osworld_all_model_summary.csv`
- `/root/liujun/saber/project/CloudTrace/processed/osworld_all_domain_summary.csv`
- `/root/liujun/saber/project/CloudTrace/reports/osworld_all_stage_resource_heatmap.svg`
