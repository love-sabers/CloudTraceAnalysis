# OSWorld-Verified P0 Summary (opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-15steps)

- Runs: 1083
- Events: 65617
- Success rate: 0.235

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|138|0.304|11.84|10.151|5355.9|49.16|
|gimp|78|0.449|9.97|8.727|4424.6|40.52|
|libreoffice_calc|141|0.092|12.92|5.228|5644.2|53.07|
|libreoffice_impress|141|0.291|9.81|6.464|4219.6|39.18|
|libreoffice_writer|69|0.217|10.28|4.23|4538.1|42.64|
|multi_apps|279|0.075|13.19|8.681|6023.9|57.31|
|os|72|0.347|8.17|20.823|3521.3|32.39|
|thunderbird|45|0.444|10.87|5.534|4951.1|46.26|
|vlc|51|0.235|11.18|25.067|5110.2|47.78|
|vs_code|69|0.435|10.29|3.751|4565.6|41.91|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
