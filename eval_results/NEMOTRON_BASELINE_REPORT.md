# Baseline Evaluation: Nemotron Lightning 3.5 30B (Base)

Evaluated across all **75 golden synthetic test cases** using Fireworks endpoint `accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b`.

## Benchmark Overview

| Metric | Score | Percentage |
|---|---|---|
| **JSON Validity** | 50 / 75 | **66.7%** |
| **Exact Pattern Accuracy** | 36 / 75 | **48.0%** |
| **Fuzzy / Semantic Pattern Accuracy** | 36 / 75 | **48.0%** |
| **Severity Classification Accuracy** | 24 / 75 | **32.0%** |
| **Escalation Decision Accuracy** | 27 / 75 | **36.0%** |
| **False Escalation Rate (Crying Wolf)** | 23 / 35 non-sev1 cases | **65.7%** |
| **Missed Escalation Rate (Missed Critical)** | 0 / 40 sev-1 cases | **0.0%** |
| **Average Latency per Case** | 25.57s | — |

---

## Pattern-by-Pattern Breakdown

| Pattern Family | Total | Valid JSON | Exact Pattern Acc | Escalation Acc | Primary Confusion / Failure |
|---|---|---|---|---|---|
| `fail_plausible_swallow` | 5 | 1 (20%) | **0 (0%)** | 1 (20%) | Swallowed plausible error narrative; timeouts |
| `state_paralysis_repetition` | 5 | 4 (80%) | **0 (0%)** | 0 (0%) | Misdiagnosed as `retry_storm_cascade` |
| `ambiguous_timeout_duplicate` | 5 | 3 (60%) | **1 (20%)** | 3 (60%) | Misdiagnosed as `retry_storm_cascade` |
| `inter_agent_trust_escalation` | 5 | 2 (40%) | **1 (20%)** | 2 (40%) | Misdiagnosed as `unsafe_automation_brittleness` |
| `agent_silo_withholding` | 5 | 4 (80%) | **2 (40%)** | 0 (0%) | Misdiagnosed as `goal_drift` / `reasoning_mismatch` |
| `goal_drift` | 5 | 4 (80%) | **2 (40%)** | 0 (0%) | Misdiagnosed as `retry_storm` / `contamination` |
| `premature_termination` | 5 | 2 (40%) | **2 (40%)** | 0 (0%) | Thinking timeouts (>60s) |
| `stale_context_execution` | 5 | 2 (40%) | **2 (40%)** | 0 (0%) | Thinking timeouts (>60s) |
| `agentic_supply_chain` | 5 | 3 (60%) | **3 (60%)** | 3 (60%) | High reasoning token count |
| `unsafe_automation_brittleness` | 5 | 4 (80%) | **3 (60%)** | 4 (80%) | Misdiagnosed as `stale_context_execution` |
| `math_in_prose` | 5 | 5 (100%) | **4 (80%)** | 2 (40%) | Falsely escalated |
| `reasoning_action_mismatch` | 5 | 4 (80%) | **4 (80%)** | 0 (0%) | Falsely escalated |
| `retry_storm_cascade` | 5 | 4 (80%) | **4 (80%)** | 4 (80%) | Strong recognition on token spikes |
| `session_contamination` | 5 | 4 (80%) | **4 (80%)** | 4 (80%) | Strong recognition on injected context |
| `visual_ui_injection` | 5 | 4 (80%) | **4 (80%)** | 4 (80%) | Strong recognition on visual DOM prompt injection |

---

## Critical Diagnostic Takeaways

1. **Unbounded Reasoning Latency (Avg: 25.6s):**
   Nemotron Lightning 3.5 30B generates 3,000–5,000 reasoning tokens per prompt. In 25 of the 75 cases (33.3%), reasoning either exceeded the HTTP timeout or hit token limits before starting to emit the JSON structure.
2. **Extreme False-Escalation Bias (65.7%):**
   Whenever the base model was uncertain, it marked `escalate: true`. Across the 35 cases where the correct answer was `escalate: false` (e.g. self-healing noise, math bugs, benign drift), it escalated 23 times.
3. **Plausibility Blindness:**
   In `fail_plausible_swallow`, the model scored 0% accuracy. Because the agent in the scenario generated fluent, valid-looking output, the base model failed to recognize that data was being dropped.
4. **Conclusion for LoRA SFT:**
   Fine-tuning with masked loss and a concise reasoning template will directly solve:
   * Immediate JSON output on token 0 (dropping latency from ~26s to ~1.5s).
   * Exact calibration of `escalate: true | false`.
   * Discrimination on near-miss pairs (`timeout_duplicate` vs `retry_storm`).
