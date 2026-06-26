# OSWorld-Verified P0 Summary (autoglm_15steps)

- Runs: 361
- Events: 17648
- Success rate: 0.446

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.457|9.85|4.105|961.3|11.0|
|gimp|26|0.538|11.42|4.862|1082.7|5.34|
|libreoffice_calc|47|0.574|7.13|1.732|741.5|6.48|
|libreoffice_impress|47|0.234|7.81|2.67|822.1|18.36|
|libreoffice_writer|23|0.478|6.48|1.368|664.9|11.38|
|multi_apps|93|0.28|11.1|2.519|1062.8|11.23|
|os|24|0.667|6.33|1.472|543.8|2.77|
|thunderbird|15|0.8|9.13|1.717|839.8|4.17|
|vlc|17|0.529|7.65|1.726|846.6|4.17|
|vs_code|23|0.609|8.78|1.663|779.7|3.85|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
