# OSWorld-Verified P0 Summary (o3_100steps)

- Runs: 369
- Events: 96416
- Success rate: 0.217

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.13|50.54|16.788|0.0|37.01|
|gimp|26|0.385|36.65|19.728|0.0|26.84|
|libreoffice_calc|47|0.106|82.28|17.141|0.0|52.63|
|libreoffice_impress|47|0.106|91.3|26.972|0.0|53.45|
|libreoffice_writer|23|0.304|74.87|14.383|0.0|48.03|
|multi_apps|101|0.139|25.57|7.79|0.0|17.45|
|os|24|0.625|23.96|22.296|0.0|16.97|
|thunderbird|15|0.267|76.4|25.163|0.0|55.15|
|vlc|17|0.294|37.76|39.832|0.0|26.96|
|vs_code|23|0.391|40.52|6.32|0.0|26.07|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
