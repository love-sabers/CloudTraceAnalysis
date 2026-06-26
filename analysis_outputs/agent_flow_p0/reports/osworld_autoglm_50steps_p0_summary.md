# OSWorld-Verified P0 Summary (autoglm_50steps)

- Runs: 361
- Events: 37142
- Success rate: 0.452

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.37|25.59|9.913|2684.5|20.24|
|gimp|26|0.577|21.54|11.133|1992.8|50.91|
|libreoffice_calc|47|0.574|10.43|1.928|1160.5|46.44|
|libreoffice_impress|47|0.255|19.68|7.392|2056.4|48.04|
|libreoffice_writer|23|0.478|14.26|3.098|1478.4|23.9|
|multi_apps|93|0.301|25.23|5.853|2443.4|37.02|
|os|24|0.667|9.21|2.176|788.3|4.01|
|thunderbird|15|0.8|18.47|3.392|2113.6|10.1|
|vlc|17|0.529|18.53|6.127|1880.6|9.05|
|vs_code|23|0.696|17.13|3.125|1624.2|30.52|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
