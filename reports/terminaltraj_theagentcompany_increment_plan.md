# TerminalTraj and TheAgentCompany Increment Plan

This plan extends the existing trace-native pipeline without introducing
hand-made 0/1/2/3 resource levels. It keeps raw downloads on the shared server
path and commits only scripts, lightweight summaries, and figures.

## Goal

Add terminal/code/company-agent coverage to the current P0 source set:

- Current sources: AgentRewardBench, OSWorld-Verified, tau-bench.
- New strict downloaded-trace source: TerminalTraj.
- New experiment candidate: TheAgentCompany.

The missing behavior class is terminal/code/container-heavy flow. It should
stress CPU, storage I/O, shell execution, dependency installation, build/test
loops, and error recovery differently from Web/GUI/tool-API flows.

## Source Decision

|source|decision|reason|
|---|---|---|
|TerminalTraj|Add to trace-native analysis now|The public dataset contains 20,000 terminal trajectories with `messages[{role, content}]`. This is a strict agent trajectory: task prompt, terminal observations, assistant plans, and shell-command batches.|
|TheAgentCompany|Do not treat as downloaded trace yet|It is highly relevant as a long-horizon office/software-company benchmark, but the public artifact is primarily an executable benchmark/environment. Unless public completed trajectories are identified, using it would require running agents ourselves.|

## TerminalTraj Processing Plan

Raw data stays on A800-dev:

`/root/liujun/saber/project/CloudTrace/raw/terminaltraj/data/`

The converter reads parquet shards and emits a unified event table:

`processed/terminaltraj_events.csv`

Each message is mapped into the existing S0-S8 flow model:

|stage|TerminalTraj interpretation|measured fields|
|---|---|---|
|S0 setup|first user prompt and terminal state|runtime log bytes, text bytes|
|S1 goal_interpretation_planning|assistant `analysis` and `plan` JSON fields|text/reasoning bytes, output token proxy|
|S2 observation_capture|terminal output in user messages|context bytes, text bytes|
|S3 context_building|terminal output retained for next decision|context bytes|
|S4 action_decision|assistant JSON response and command selection|LLM output token proxy, action bytes|
|S5 actuation|`commands[].keystrokes` emitted by the assistant|tool/action bytes, command count|
|S6 environment_result_wait|terminal output after commands|runtime log/text bytes|
|S7 feedback_error_recovery|terminal observations with failure/error patterns|retry/error count, text bytes|
|S8 validation_finalization|assistant message with `task_complete=true`|text bytes|

The primary measured quantities are bytes and counts present in the trace:

- command bytes
- terminal output bytes
- assistant analysis/plan bytes
- number of shell command actions
- retry/error proxy from observed terminal failure text
- discrete trace length through event counts

Token counts are byte-derived proxies because TerminalTraj does not include
provider token accounting.

## TheAgentCompany Processing Plan

TheAgentCompany should be added through a separate runnable experiment path:

1. Run a small benchmark subset on A800-dev using the official environment.
2. Attach OpenTelemetry/Langfuse/Phoenix-style spans around LLM calls, tool
   calls, shell/browser actions, file edits, and validators.
3. Collect hardware counters during each span:
   CPU time, RSS/peak memory, disk read/write bytes, network bytes, GPU time
   if model inference is local, and browser/container overhead.
4. Convert spans into the same S0-S8 event schema.

This is intentionally separated from the downloaded-trace pipeline because it
would be a self-run experiment rather than second-hand public trace analysis.

## Expected Comparison Value

After TerminalTraj is added, the source taxonomy becomes:

|source class|representative source|expected dominant hardware behavior|
|---|---|---|
|Web/browser agent|AgentRewardBench|LLM context/action loops, browser observation/action|
|Desktop GUI agent|OSWorld-Verified|screenshot/visual bytes, GUI action, long context|
|Tool/API agent|tau-bench|LLM/tool-call cycles with low display pressure|
|Terminal/code agent|TerminalTraj|shell commands, build/test logs, CPU/storage/container-heavy recovery|
|Long-horizon office/software worker|TheAgentCompany|candidate for later self-run instrumentation|

## Acceptance Criteria

- `processed/terminaltraj_events.csv` exists and uses the unified event schema.
- `processed/trace_native_run_stage_metrics.csv` includes `TerminalTraj`.
- Visual profiles include a TerminalTraj panel.
- The report explicitly marks TerminalTraj token counts as byte-derived proxy
  and TheAgentCompany as not yet a downloaded trace source.
