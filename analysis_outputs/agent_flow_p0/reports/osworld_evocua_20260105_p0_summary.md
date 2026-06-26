# OSWorld-Verified P0 Summary (evocua_20260105)

- Runs: 361
- Events: 52511
- Success rate: 0.551

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.63|25.91|10.632|3275.9|17.96|
|gimp|26|0.769|17.27|9.436|2022.6|14.62|
|libreoffice_calc|47|0.553|27.96|6.087|3353.5|24.7|
|libreoffice_impress|47|0.574|24.09|8.051|2733.9|18.84|
|libreoffice_writer|23|0.652|19.35|4.083|2322.1|18.37|
|multi_apps|93|0.258|40.89|16.237|4910.6|45.64|
|os|24|0.75|16.88|23.383|2061.7|20.37|
|thunderbird|15|0.8|20.93|5.3|2597.8|18.31|
|vlc|17|0.471|31.06|34.5|3757.3|34.38|
|vs_code|23|0.87|28.3|6.219|3529.1|21.24|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
