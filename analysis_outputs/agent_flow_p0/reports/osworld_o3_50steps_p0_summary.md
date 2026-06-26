# OSWorld-Verified P0 Summary (o3_50steps)

- Runs: 369
- Events: 71178
- Success rate: 0.163

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.217|36.52|11.905|0.0|30.06|
|gimp|26|0.385|33.27|16.766|0.0|24.8|
|libreoffice_calc|47|0.085|47.34|9.622|0.0|33.09|
|libreoffice_impress|47|0.043|48.17|15.126|0.0|31.1|
|libreoffice_writer|23|0.174|39.26|8.026|0.0|29.12|
|multi_apps|101|0.109|35.13|12.469|0.0|25.57|
|os|24|0.375|20.75|21.943|0.0|14.49|
|thunderbird|15|0.2|41.87|11.192|0.0|30.38|
|vlc|17|0.118|33.06|37.127|0.0|26.07|
|vs_code|23|0.217|35.87|5.63|0.0|25.29|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
