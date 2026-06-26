# OSWorld-Verified P0 Summary (mobile-agent-v3-gui-owl-7b)

- Runs: 361
- Events: 21692
- Success rate: 0.313

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.391|10.52|4.87|1215.3|0.0|
|gimp|26|0.654|10.81|4.517|1288.5|0.0|
|libreoffice_calc|47|0.17|12.94|2.573|1569.2|0.0|
|libreoffice_impress|47|0.17|10.0|3.314|1151.2|0.0|
|libreoffice_writer|23|0.478|8.61|1.832|999.0|0.0|
|multi_apps|93|0.097|13.3|4.757|1554.5|0.0|
|os|24|0.5|10.88|11.958|1322.4|0.0|
|thunderbird|15|0.667|11.13|3.009|1333.9|0.0|
|vlc|17|0.294|9.82|11.148|1201.8|0.0|
|vs_code|23|0.652|10.35|1.716|1302.1|0.0|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
