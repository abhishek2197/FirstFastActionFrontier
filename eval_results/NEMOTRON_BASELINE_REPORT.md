# Baseline Evaluation: Nemotron Lightning 3.5 30B (Base)

Evaluated on 15 synthetic test cases using Fireworks endpoint `accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b`.

## Overall Metrics

| Metric | Score | Percentage |
|---|---|---|
| **JSON Validity** | 7 / 15 | 46.7% |
| **Exact Pattern Match** | 4 / 15 | 26.7% |
| **Fuzzy / Semantic Pattern Match** | 4 / 15 | 26.7% |
| **Severity Accuracy** | 3 / 15 | 20.0% |
| **Escalation Accuracy** | 4 / 15 | 26.7% |
| **False Escalation Rate** | 3 cases | 20.0% |
| **Missed Escalation Rate** | 0 cases | 0.0% |
| **Average Latency** | 26.05s | - |

## Per-Case Breakdown

| Case ID | Gold Pattern | Pred Pattern | Match | Gold Sev | Pred Sev | Escalate Match |
|---|---|---|---|---|---|---|
| `inc_retry_storm_cascade_01` | `retry_storm_cascade` | `retry_storm_cascade` | Exact | sev-1 | sev-1 | True |
| `inc_ambiguous_timeout_duplicate_01` | `ambiguous_timeout_duplicate` | `retry_storm_cascade` | Miss | sev-1 | sev-2 | True |
| `inc_math_in_prose_01` | `math_in_prose` | `math_in_prose` | Exact | sev-3 | sev-2 | False |
| `inc_session_contamination_01` | `session_contamination` | `session_contamination` | Exact | sev-2 | sev-2 | True |
| `inc_inter_agent_trust_escalation_01` | `inter_agent_trust_escalation` | `unsafe_automation_brittleness` | Miss | sev-1 | sev-1 | True |
| `inc_fail_plausible_swallow_01` | `fail_plausible_swallow` | `N/A` | Miss | None | None | False |
| `inc_reasoning_action_mismatch_01` | `reasoning_action_mismatch` | `unsafe_automation_brittleness` | Miss | sev-2 | sev-1 | False |
| `inc_goal_drift_01` | `goal_drift` | `N/A` | Miss | None | None | False |
| `inc_stale_context_execution_01` | `stale_context_execution` | `stale_context_execution` | Exact | sev-2 | sev-1 | False |
| `inc_agent_silo_withholding_01` | `agent_silo_withholding` | `N/A` | Miss | None | None | False |
| `inc_state_paralysis_repetition_01` | `state_paralysis_repetition` | `N/A` | Miss | None | None | False |
| `inc_agentic_supply_chain_01` | `agentic_supply_chain` | `N/A` | Miss | None | None | False |
| `inc_visual_ui_injection_01` | `visual_ui_injection` | `N/A` | Miss | None | None | False |
| `inc_premature_termination_01` | `premature_termination` | `N/A` | Miss | None | None | False |
| `inc_unsafe_automation_brittleness_01` | `unsafe_automation_brittleness` | `N/A` | Miss | None | None | False |
