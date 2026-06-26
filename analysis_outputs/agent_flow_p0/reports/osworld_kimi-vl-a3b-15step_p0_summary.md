# OSWorld-Verified P0 Summary (kimi-vl-a3b-15step)

- Runs: 361
- Events: 24273
- Success rate: 0.094

## Domain Summary

|domain|runs|success_rate|avg_steps|avg_screenshot_mb|avg_response_tokens|avg_runtime_log_kb|
|---|---|---|---|---|---|---|
|chrome|46|0.239|12.02|5.399|4281.0|40.62|
|gimp|26|0.154|12.5|6.381|4576.6|42.99|
|libreoffice_calc|47|0.043|12.62|2.535|4733.3|45.59|
|libreoffice_impress|47|0.106|11.81|3.997|4367.9|41.51|
|libreoffice_writer|23|0.087|12.0|2.527|4475.9|43.14|
|multi_apps|93|0.011|14.14|4.748|5139.8|50.59|
|os|24|0.0|12.92|7.763|4671.0|43.98|
|thunderbird|15|0.2|13.6|4.276|4940.9|47.74|
|vlc|17|0.176|11.76|13.647|4103.5|39.77|
|vs_code|23|0.13|12.35|2.263|4419.0|41.81|

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
