# OSWorld-Verified P0 Summary (jedi-7b-4o-15steps)

- Runs: 361
- Events: 20677
- Success rate: 0.258

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.283|10.67|4.39|0.0|6.79|
|gimp|26|0.692|8.85|4.578|0.0|5.08|
|libreoffice_calc|47|0.064|13.38|2.688|0.0|9.06|
|libreoffice_impress|47|0.128|11.02|3.586|0.0|6.18|
|libreoffice_writer|23|0.435|10.17|2.004|0.0|7.0|
|multi_apps|93|0.086|11.43|4.099|0.0|7.58|
|os|24|0.458|7.83|8.888|0.0|4.79|
|thunderbird|15|0.533|9.67|2.778|0.0|5.96|
|vlc|17|0.235|10.65|9.926|0.0|6.57|
|vs_code|23|0.522|10.22|1.746|0.0|5.85|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
