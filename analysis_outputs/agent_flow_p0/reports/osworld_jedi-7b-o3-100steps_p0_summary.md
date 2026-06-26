# OSWorld-Verified P0 Summary (jedi-7b-o3-100steps)

- Runs: 361
- Events: 49676
- Success rate: 0.496

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.587|30.57|14.796|0.0|16.41|
|gimp|26|0.692|23.65|8.518|0.0|12.71|
|libreoffice_calc|47|0.426|25.17|5.646|0.0|11.81|
|libreoffice_impress|47|0.426|22.23|7.677|0.0|12.63|
|libreoffice_writer|23|0.522|30.09|6.144|0.0|15.77|
|multi_apps|93|0.323|31.68|12.408|0.0|14.5|
|os|24|0.5|26.42|33.938|0.0|11.76|
|thunderbird|15|0.8|22.93|6.038|0.0|11.56|
|vlc|17|0.529|24.71|23.44|0.0|13.02|
|vs_code|23|0.826|17.87|3.053|0.0|8.93|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
