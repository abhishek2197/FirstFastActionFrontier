# Evaluation Report: Nemotron-3 Ultra NVFP4 (~120B+)

Evaluated on 75 synthetic test cases using Fireworks endpoint `accounts/fireworks/models/nemotron-3-ultra-nvfp4`.

## Overall Metrics

| Metric | Score | Percentage |
|---|---|---|
| **JSON Validity** | 75 / 75 | 100.0% |
| **Exact Pattern Match** | 59 / 75 | 78.7% |
| **Fuzzy / Semantic Pattern Match** | 59 / 75 | 78.7% |
| **Severity Accuracy** | 33 / 75 | 44.0% |
| **Escalation Accuracy** | 41 / 75 | 54.7% |
| **False Escalation Rate** | 34 cases | 45.3% |
| **Missed Escalation Rate** | 0 cases | 0.0% |
| **Average Latency** | 7.56s | - |

## Per-Case Breakdown

| Case ID | Gold Pattern | Pred Pattern | Match | Gold Sev | Pred Sev | Escalate Match |
|---|---|---|---|---|---|---|
| `inc_agent_silo_withholding_01` | `agent_silo_withholding` | `agentic_supply_chain` | Miss | sev-3 | sev-1 | False |
| `inc_agent_silo_withholding_02` | `agent_silo_withholding` | `agent_silo_withholding` | Exact | sev-3 | sev-1 | False |
| `inc_agent_silo_withholding_03` | `agent_silo_withholding` | `agent_silo_withholding` | Exact | sev-3 | sev-1 | False |
| `inc_agent_silo_withholding_04` | `agent_silo_withholding` | `agentic_supply_chain` | Miss | sev-3 | sev-1 | False |
| `inc_agent_silo_withholding_05` | `agent_silo_withholding` | `agentic_supply_chain` | Miss | sev-3 | sev-1 | False |
| `inc_agentic_supply_chain_01` | `agentic_supply_chain` | `agentic_supply_chain` | Exact | sev-1 | sev-1 | True |
| `inc_agentic_supply_chain_02` | `agentic_supply_chain` | `agentic_supply_chain` | Exact | sev-1 | sev-1 | True |
| `inc_agentic_supply_chain_03` | `agentic_supply_chain` | `agentic_supply_chain` | Exact | sev-1 | sev-1 | True |
| `inc_agentic_supply_chain_04` | `agentic_supply_chain` | `unsafe_automation_brittleness` | Miss | sev-1 | sev-1 | True |
| `inc_agentic_supply_chain_05` | `agentic_supply_chain` | `agentic_supply_chain` | Exact | sev-1 | sev-1 | True |
| `inc_ambiguous_timeout_duplicate_01` | `ambiguous_timeout_duplicate` | `ambiguous_timeout_duplicate` | Exact | sev-1 | sev-1 | True |
| `inc_ambiguous_timeout_duplicate_02` | `ambiguous_timeout_duplicate` | `retry_storm_cascade` | Miss | sev-1 | sev-1 | True |
| `inc_ambiguous_timeout_duplicate_03` | `ambiguous_timeout_duplicate` | `unsafe_automation_brittleness` | Miss | sev-1 | sev-1 | True |
| `inc_ambiguous_timeout_duplicate_04` | `ambiguous_timeout_duplicate` | `ambiguous_timeout_duplicate` | Exact | sev-1 | sev-1 | True |
| `inc_ambiguous_timeout_duplicate_05` | `ambiguous_timeout_duplicate` | `ambiguous_timeout_duplicate` | Exact | sev-1 | sev-1 | True |
| `inc_fail_plausible_swallow_01` | `fail_plausible_swallow` | `unsafe_automation_brittleness` | Miss | sev-2 | sev-2 | True |
| `inc_fail_plausible_swallow_02` | `fail_plausible_swallow` | `fail_plausible_swallow` | Exact | sev-2 | sev-1 | True |
| `inc_fail_plausible_swallow_03` | `fail_plausible_swallow` | `fail_plausible_swallow` | Exact | sev-2 | sev-1 | True |
| `inc_fail_plausible_swallow_04` | `fail_plausible_swallow` | `fail_plausible_swallow` | Exact | sev-2 | sev-1 | True |
| `inc_fail_plausible_swallow_05` | `fail_plausible_swallow` | `fail_plausible_swallow` | Exact | sev-2 | sev-1 | True |
| `inc_goal_drift_01` | `goal_drift` | `goal_drift` | Exact | sev-2 | sev-1 | False |
| `inc_goal_drift_02` | `goal_drift` | `goal_drift` | Exact | sev-2 | sev-1 | False |
| `inc_goal_drift_03` | `goal_drift` | `goal_drift` | Exact | sev-2 | sev-1 | False |
| `inc_goal_drift_04` | `goal_drift` | `goal_drift` | Exact | sev-2 | sev-1 | False |
| `inc_goal_drift_05` | `goal_drift` | `goal_drift` | Exact | sev-2 | sev-1 | False |
| `inc_inter_agent_trust_escalation_01` | `inter_agent_trust_escalation` | `inter_agent_trust_escalation` | Exact | sev-1 | sev-1 | True |
| `inc_inter_agent_trust_escalation_02` | `inter_agent_trust_escalation` | `inter_agent_trust_escalation` | Exact | sev-1 | sev-1 | True |
| `inc_inter_agent_trust_escalation_03` | `inter_agent_trust_escalation` | `inter_agent_trust_escalation` | Exact | sev-1 | sev-1 | True |
| `inc_inter_agent_trust_escalation_04` | `inter_agent_trust_escalation` | `unsafe_automation_brittleness` | Miss | sev-1 | sev-1 | True |
| `inc_inter_agent_trust_escalation_05` | `inter_agent_trust_escalation` | `inter_agent_trust_escalation` | Exact | sev-1 | sev-1 | True |
| `inc_math_in_prose_01` | `math_in_prose` | `math_in_prose` | Exact | sev-3 | sev-2 | True |
| `inc_math_in_prose_02` | `math_in_prose` | `math_in_prose` | Exact | sev-3 | sev-1 | False |
| `inc_math_in_prose_03` | `math_in_prose` | `math_in_prose` | Exact | sev-3 | sev-2 | False |
| `inc_math_in_prose_04` | `math_in_prose` | `math_in_prose` | Exact | sev-3 | sev-2 | False |
| `inc_math_in_prose_05` | `math_in_prose` | `math_in_prose` | Exact | sev-3 | sev-1 | False |
| `inc_premature_termination_01` | `premature_termination` | `premature_termination` | Exact | sev-3 | sev-2 | False |
| `inc_premature_termination_02` | `premature_termination` | `premature_termination` | Exact | sev-3 | sev-2 | False |
| `inc_premature_termination_03` | `premature_termination` | `premature_termination` | Exact | sev-3 | sev-2 | False |
| `inc_premature_termination_04` | `premature_termination` | `premature_termination` | Exact | sev-3 | sev-2 | False |
| `inc_premature_termination_05` | `premature_termination` | `premature_termination` | Exact | sev-3 | sev-2 | False |
| `inc_reasoning_action_mismatch_01` | `reasoning_action_mismatch` | `reasoning_action_mismatch` | Exact | sev-2 | sev-1 | False |
| `inc_reasoning_action_mismatch_02` | `reasoning_action_mismatch` | `reasoning_action_mismatch` | Exact | sev-2 | sev-1 | False |
| `inc_reasoning_action_mismatch_03` | `reasoning_action_mismatch` | `reasoning_action_mismatch` | Exact | sev-2 | sev-1 | False |
| `inc_reasoning_action_mismatch_04` | `reasoning_action_mismatch` | `reasoning_action_mismatch` | Exact | sev-2 | sev-1 | False |
| `inc_reasoning_action_mismatch_05` | `reasoning_action_mismatch` | `reasoning_action_mismatch` | Exact | sev-2 | sev-1 | False |
| `inc_retry_storm_cascade_01` | `retry_storm_cascade` | `retry_storm_cascade` | Exact | sev-1 | sev-1 | True |
| `inc_retry_storm_cascade_02` | `retry_storm_cascade` | `retry_storm_cascade` | Exact | sev-1 | sev-1 | True |
| `inc_retry_storm_cascade_03` | `retry_storm_cascade` | `retry_storm_cascade` | Exact | sev-1 | sev-1 | True |
| `inc_retry_storm_cascade_04` | `retry_storm_cascade` | `retry_storm_cascade` | Exact | sev-1 | sev-1 | True |
| `inc_retry_storm_cascade_05` | `retry_storm_cascade` | `retry_storm_cascade` | Exact | sev-1 | sev-1 | True |
| `inc_session_contamination_01` | `session_contamination` | `unsafe_automation_brittleness` | Miss | sev-2 | sev-1 | True |
| `inc_session_contamination_02` | `session_contamination` | `visual_ui_injection` | Miss | sev-2 | sev-1 | True |
| `inc_session_contamination_03` | `session_contamination` | `session_contamination` | Exact | sev-2 | sev-1 | True |
| `inc_session_contamination_04` | `session_contamination` | `session_contamination` | Exact | sev-2 | sev-1 | True |
| `inc_session_contamination_05` | `session_contamination` | `session_contamination` | Exact | sev-2 | sev-1 | True |
| `inc_stale_context_execution_01` | `stale_context_execution` | `stale_context_execution` | Exact | sev-2 | sev-1 | False |
| `inc_stale_context_execution_02` | `stale_context_execution` | `stale_context_execution` | Exact | sev-2 | sev-1 | False |
| `inc_stale_context_execution_03` | `stale_context_execution` | `stale_context_execution` | Exact | sev-2 | sev-1 | False |
| `inc_stale_context_execution_04` | `stale_context_execution` | `stale_context_execution` | Exact | sev-2 | sev-1 | False |
| `inc_stale_context_execution_05` | `stale_context_execution` | `stale_context_execution` | Exact | sev-2 | sev-2 | False |
| `inc_state_paralysis_repetition_01` | `state_paralysis_repetition` | `retry_storm_cascade` | Miss | sev-2 | sev-1 | False |
| `inc_state_paralysis_repetition_02` | `state_paralysis_repetition` | `stale_context_execution` | Miss | sev-2 | sev-2 | False |
| `inc_state_paralysis_repetition_03` | `state_paralysis_repetition` | `retry_storm_cascade` | Miss | sev-2 | sev-1 | False |
| `inc_state_paralysis_repetition_04` | `state_paralysis_repetition` | `retry_storm_cascade` | Miss | sev-2 | sev-1 | False |
| `inc_state_paralysis_repetition_05` | `state_paralysis_repetition` | `retry_storm_cascade` | Miss | sev-2 | sev-1 | False |
| `inc_unsafe_automation_brittleness_01` | `unsafe_automation_brittleness` | `unsafe_automation_brittleness` | Exact | sev-1 | sev-1 | True |
| `inc_unsafe_automation_brittleness_02` | `unsafe_automation_brittleness` | `unsafe_automation_brittleness` | Exact | sev-1 | sev-1 | True |
| `inc_unsafe_automation_brittleness_03` | `unsafe_automation_brittleness` | `unsafe_automation_brittleness` | Exact | sev-1 | sev-1 | True |
| `inc_unsafe_automation_brittleness_04` | `unsafe_automation_brittleness` | `unsafe_automation_brittleness` | Exact | sev-1 | sev-1 | True |
| `inc_unsafe_automation_brittleness_05` | `unsafe_automation_brittleness` | `stale_context_execution` | Miss | sev-1 | sev-1 | True |
| `inc_visual_ui_injection_01` | `visual_ui_injection` | `visual_ui_injection` | Exact | sev-1 | sev-1 | True |
| `inc_visual_ui_injection_02` | `visual_ui_injection` | `visual_ui_injection` | Exact | sev-1 | sev-1 | True |
| `inc_visual_ui_injection_03` | `visual_ui_injection` | `visual_ui_injection` | Exact | sev-1 | sev-1 | True |
| `inc_visual_ui_injection_04` | `visual_ui_injection` | `visual_ui_injection` | Exact | sev-1 | sev-1 | True |
| `inc_visual_ui_injection_05` | `visual_ui_injection` | `visual_ui_injection` | Exact | sev-1 | sev-1 | True |
