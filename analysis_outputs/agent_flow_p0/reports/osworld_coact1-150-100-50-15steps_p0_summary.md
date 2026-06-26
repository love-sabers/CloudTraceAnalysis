# OSWorld-Verified P0 Summary (coact1-150-100-50-15steps)

- Runs: 0
- Events: 0
- Success rate: n/a

## Domain Summary

No `traj.jsonl` task directories were recognized in this archive.

## Interpretation

- OSWorld introduces real desktop/GUI/VM phases absent from tau-bench and stronger than web-only AgentRewardBench.
- S0/S5/S6/S8 carry VM/container, display, CPU, and storage demand due to environment setup, desktop actuation, screenshots, app execution, and execution-based validation.
- S1/S4 remain accelerator/HBM dominated because each step requires model reasoning and action synthesis.
