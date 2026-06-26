# OSWorld-Verified P0 Summary (evocua_8b_20260105)

- Runs: 361
- Events: 57373
- Success rate: 0.446

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.522|29.67|11.95|3863.9|20.32|
|gimp|26|0.846|16.77|6.1|2070.2|18.2|
|libreoffice_calc|47|0.298|36.47|7.726|4486.5|32.94|
|libreoffice_impress|47|0.362|23.53|8.026|2827.7|19.74|
|libreoffice_writer|23|0.478|27.48|5.881|3524.6|23.79|
|multi_apps|93|0.247|42.03|14.91|5330.5|54.66|
|os|24|0.75|20.67|27.923|2570.3|26.06|
|thunderbird|15|0.733|20.27|5.021|2855.2|16.05|
|vlc|17|0.353|29.0|29.026|3789.7|26.55|
|vs_code|23|0.652|30.35|5.552|3932.6|23.08|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
