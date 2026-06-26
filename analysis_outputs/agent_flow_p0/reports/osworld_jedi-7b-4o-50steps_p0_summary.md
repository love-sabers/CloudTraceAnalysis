# OSWorld-Verified P0 Summary (jedi-7b-4o-50steps)

- Runs: 361
- Events: 45787
- Success rate: 0.258

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.304|23.33|9.267|0.0|13.04|
|gimp|26|0.615|19.08|7.649|0.0|10.07|
|libreoffice_calc|47|0.064|29.6|6.071|0.0|20.99|
|libreoffice_impress|47|0.149|28.94|9.102|0.0|16.75|
|libreoffice_writer|23|0.261|20.57|4.228|0.0|14.08|
|multi_apps|93|0.151|26.83|10.621|0.0|17.78|
|os|24|0.458|21.12|24.613|0.0|12.17|
|thunderbird|15|0.467|14.6|3.908|0.0|8.56|
|vlc|17|0.235|21.65|25.137|0.0|12.07|
|vs_code|23|0.478|23.65|4.799|0.0|14.07|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
