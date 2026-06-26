# OSWorld-Verified P0 Summary (kimi-k25)

- Runs: 359
- Events: 49082
- Success rate: 0.618

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|45|0.622|25.16|11.545|7322.3|98.94|
|gimp|26|0.692|25.12|11.512|6999.9|100.76|
|libreoffice_calc|47|0.681|28.11|6.033|5444.6|75.38|
|libreoffice_impress|47|0.638|17.23|5.361|3497.0|48.6|
|libreoffice_writer|23|0.739|17.22|3.858|3074.4|44.3|
|multi_apps|93|0.43|40.46|13.657|7407.2|112.87|
|os|24|0.708|13.58|14.087|2415.9|35.89|
|thunderbird|15|0.8|20.2|5.267|4603.9|63.01|
|vlc|17|0.588|19.94|20.083|3942.6|60.5|
|vs_code|22|0.818|23.09|4.941|5309.5|78.11|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
