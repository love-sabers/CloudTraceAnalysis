# OSWorld-Verified P0 Summary (kimi-vl-a3b-100step)

- Runs: 361
- Events: 94354
- Success rate: 0.097

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.217|40.65|20.184|14363.6|136.86|
|gimp|26|0.115|39.27|26.465|13829.4|130.93|
|libreoffice_calc|47|0.021|54.32|11.227|20497.7|198.31|
|libreoffice_impress|47|0.064|38.11|13.368|13678.4|131.68|
|libreoffice_writer|23|0.087|42.83|9.282|15575.5|150.24|
|multi_apps|93|0.011|64.78|19.851|23414.2|231.18|
|os|24|0.125|61.71|36.339|22279.5|210.63|
|thunderbird|15|0.2|58.87|17.422|21774.4|211.76|
|vlc|17|0.176|51.59|56.5|18073.2|175.57|
|vs_code|23|0.261|40.17|9.185|14785.0|139.96|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
