# OSWorld-Verified P0 Summary (claude-3-7-sonnet-20250219-15steps)

- Runs: 361
- Events: 23784
- Success rate: 0.263

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.391|12.35|6.837|0.0|20.12|
|gimp|26|0.346|11.19|8.559|0.0|18.29|
|libreoffice_calc|47|0.085|13.83|2.755|0.0|20.65|
|libreoffice_impress|47|0.277|12.0|3.911|0.0|18.89|
|libreoffice_writer|23|0.348|12.48|3.115|0.0|20.06|
|multi_apps|93|0.108|13.89|7.061|0.0|21.7|
|os|24|0.5|10.0|11.499|0.0|17.33|
|thunderbird|15|0.333|12.67|3.775|0.0|20.06|
|vlc|17|0.353|10.47|11.689|0.0|18.29|
|vs_code|23|0.435|12.13|2.044|0.0|19.35|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
