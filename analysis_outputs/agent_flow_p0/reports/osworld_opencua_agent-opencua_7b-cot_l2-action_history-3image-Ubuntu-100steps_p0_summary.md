# OSWorld-Verified P0 Summary (opencua_agent-opencua_7b-cot_l2-action_history-3image-Ubuntu-100steps)

- Runs: 1083
- Events: 128799
- Success rate: 0.257

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|138|0.341|19.75|17.288|9098.1|83.38|
|gimp|78|0.474|21.78|16.821|10134.5|92.76|
|libreoffice_calc|141|0.106|26.45|10.908|11831.1|111.31|
|libreoffice_impress|141|0.305|16.03|10.842|7094.8|66.23|
|libreoffice_writer|69|0.232|16.3|6.993|7253.6|68.34|
|multi_apps|279|0.093|31.47|20.152|14592.7|138.95|
|os|72|0.417|11.33|28.612|4982.1|45.68|
|thunderbird|45|0.4|32.44|15.324|15690.3|146.27|
|vlc|51|0.294|16.63|35.197|7740.5|72.22|
|vs_code|69|0.449|20.9|8.616|9398.5|86.37|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
