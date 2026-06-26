# OSWorld-Verified P0 Summary (claude-sonnet-4-5-20250929_100steps)

- Runs: 361
- Events: 59197
- Success rate: 0.601

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.609|29.8|13.398|2179.4|75.69|
|gimp|26|0.538|21.58|10.461|1190.0|53.16|
|libreoffice_calc|47|0.723|32.06|6.987|2074.1|87.7|
|libreoffice_impress|47|0.66|19.04|6.621|1271.9|50.16|
|libreoffice_writer|23|0.739|31.91|6.973|2210.6|95.21|
|multi_apps|93|0.441|51.55|18.911|3003.2|164.06|
|os|24|0.708|14.96|20.431|807.0|40.35|
|thunderbird|15|0.6|21.0|5.058|1369.9|63.57|
|vlc|17|0.529|19.0|19.061|1283.6|51.32|
|vs_code|23|0.739|30.96|5.945|1755.3|91.09|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
