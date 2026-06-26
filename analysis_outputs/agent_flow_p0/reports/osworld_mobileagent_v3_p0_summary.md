# OSWorld-Verified P0 Summary (mobileagent_v3)

- Runs: 361
- Events: 47641
- Success rate: 0.374

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.478|20.48|9.109|0.0|0.0|
|gimp|26|0.615|19.27|6.22|0.0|0.0|
|libreoffice_calc|47|0.128|26.62|5.043|0.0|0.0|
|libreoffice_impress|47|0.277|21.45|8.064|0.0|0.0|
|libreoffice_writer|23|0.478|23.52|4.962|0.0|0.0|
|multi_apps|93|0.194|36.3|10.586|0.0|0.0|
|os|24|0.583|19.83|24.59|0.0|0.0|
|thunderbird|15|0.6|20.73|9.769|0.0|0.0|
|vlc|17|0.412|29.29|33.077|0.0|0.0|
|vs_code|23|0.826|17.3|3.102|0.0|0.0|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
