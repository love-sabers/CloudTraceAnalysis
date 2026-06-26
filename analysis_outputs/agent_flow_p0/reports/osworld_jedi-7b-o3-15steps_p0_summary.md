# OSWorld-Verified P0 Summary (jedi-7b-o3-15steps)

- Runs: 361
- Events: 20815
- Success rate: 0.416

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.5|10.85|4.455|0.0|6.5|
|gimp|26|0.654|9.19|4.09|0.0|5.89|
|libreoffice_calc|47|0.298|12.45|2.598|0.0|7.03|
|libreoffice_impress|47|0.404|11.17|3.734|0.0|6.37|
|libreoffice_writer|23|0.609|9.65|1.943|0.0|5.67|
|multi_apps|93|0.204|12.53|4.817|0.0|7.42|
|os|24|0.5|7.46|8.304|0.0|5.04|
|thunderbird|15|0.733|10.0|2.546|0.0|6.23|
|vlc|17|0.471|9.94|10.552|0.0|6.13|
|vs_code|23|0.565|9.09|1.614|0.0|5.26|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
