# OSWorld-Verified P0 Summary (opencua_agent-opencua_32b-cot_l2-action_history-3image-Ubuntu-50steps)

- Runs: 1083
- Events: 110633
- Success rate: 0.331

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|138|0.413|16.93|15.441|7853.4|71.96|
|gimp|78|0.692|16.12|14.704|7418.3|67.84|
|libreoffice_calc|141|0.135|22.94|9.683|10213.0|96.46|
|libreoffice_impress|141|0.362|13.82|9.406|5941.8|55.43|
|libreoffice_writer|69|0.362|16.17|7.848|7129.1|67.58|
|multi_apps|279|0.143|28.99|18.883|13560.5|129.04|
|os|72|0.514|11.83|25.03|5157.1|47.71|
|thunderbird|45|0.533|16.91|9.39|7877.2|73.8|
|vlc|51|0.255|12.2|26.575|5612.1|52.28|
|vs_code|69|0.551|14.83|5.819|6645.4|61.14|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
