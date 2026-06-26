# OSWorld-Verified P0 Summary (opencua_agent-opencua_a3b-cot_l2-action_history-3image-Ubuntu-100step)

- Runs: 361
- Events: 44666
- Success rate: 0.169

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.239|14.54|6.585|6565.6|60.37|
|gimp|26|0.538|23.65|11.177|11323.8|103.27|
|libreoffice_calc|47|0.064|30.47|5.987|13464.2|127.76|
|libreoffice_impress|47|0.234|15.81|5.16|6964.6|65.41|
|libreoffice_writer|23|0.13|14.96|3.206|6710.0|62.67|
|multi_apps|93|0.022|35.49|13.486|16357.6|154.92|
|os|24|0.125|17.96|12.796|8280.2|75.43|
|thunderbird|15|0.2|18.67|5.976|8508.6|79.32|
|vlc|17|0.118|22.29|28.534|10296.5|95.49|
|vs_code|23|0.391|17.22|3.509|7666.7|70.09|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
