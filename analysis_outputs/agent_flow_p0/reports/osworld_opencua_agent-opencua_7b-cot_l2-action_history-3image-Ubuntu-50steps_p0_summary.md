# OSWorld-Verified P0 Summary (opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-50steps)

- Runs: 1082
- Events: 112711
- Success rate: 0.270

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|138|0.362|16.82|14.324|7696.6|70.55|
|gimp|78|0.436|18.55|14.161|8466.0|77.54|
|libreoffice_calc|140|0.121|24.85|10.11|11011.3|103.46|
|libreoffice_impress|141|0.312|13.89|9.053|6128.1|57.05|
|libreoffice_writer|69|0.29|16.17|7.466|7317.3|68.89|
|multi_apps|279|0.115|27.24|17.218|12670.5|120.51|
|os|72|0.417|10.83|28.448|4689.3|43.21|
|thunderbird|45|0.422|19.64|10.84|9408.9|87.53|
|vlc|51|0.275|18.37|37.351|8536.5|79.87|
|vs_code|69|0.464|16.93|6.463|7532.4|69.23|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
