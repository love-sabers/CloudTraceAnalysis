# OSWorld-Verified P0 Summary (UI-TARS-0717-100step)

- Runs: 361
- Events: 56769
- Success rate: 0.388

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.565|23.85|10.217|0.0|2.58|
|gimp|26|0.5|15.38|6.928|0.0|1.67|
|libreoffice_calc|47|0.34|38.68|8.094|0.0|4.2|
|libreoffice_impress|47|0.468|27.98|9.551|0.0|3.04|
|libreoffice_writer|23|0.522|21.13|6.437|0.0|2.3|
|multi_apps|93|0.129|49.55|16.728|0.0|5.4|
|os|24|0.375|22.54|19.552|0.0|2.5|
|thunderbird|15|0.733|10.13|2.586|0.0|1.1|
|vlc|17|0.353|12.94|12.962|0.0|1.4|
|vs_code|23|0.565|21.43|3.528|0.0|2.33|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
