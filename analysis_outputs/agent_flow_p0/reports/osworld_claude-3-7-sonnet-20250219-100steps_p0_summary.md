# OSWorld-Verified P0 Summary (claude-3-7-sonnet-20250219-100steps)

- Runs: 361
- Events: 56185
- Success rate: 0.343

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.522|23.52|13.597|0.0|36.88|
|gimp|26|0.423|17.54|13.895|0.0|29.94|
|libreoffice_calc|47|0.213|34.51|7.047|0.0|48.06|
|libreoffice_impress|47|0.298|21.02|6.74|0.0|31.1|
|libreoffice_writer|23|0.435|32.17|6.901|0.0|48.24|
|multi_apps|93|0.183|43.33|18.274|0.0|66.93|
|os|24|0.458|16.33|18.792|0.0|27.32|
|thunderbird|15|0.667|31.8|11.432|0.0|49.61|
|vlc|17|0.235|28.29|30.102|0.0|43.68|
|vs_code|23|0.565|32.35|7.468|0.0|48.81|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
