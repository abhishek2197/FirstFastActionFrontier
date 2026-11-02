# Minute Five Synthetic Benchmark Dataset

Generated using `accounts/fireworks/models/glm-5p3` via Fireworks AI across the 15 production AI agent failure patterns defined in [`PATTERNS.md`](../PATTERNS.md).

## Dataset Summary

* **Total Test Cases:** 75 (5 cases per pattern family)
* **Format:** 
  * `synthetic_test_cases.jsonl`: One JSON object per line (OpenAI/Fireworks chat `messages` format with structured `gold_triage`).
  * `synthetic_test_cases.json`: Formatted JSON array for inspection and tooling.
* **Target Scenario:** Minute-Five incident triage (alerts, noisy log excerpt, context).

## Pattern Distribution (5 cases each)

| Pattern | Tag | Baseline Severity | Escalate |
|---|---|---|---|
| The "Fail-Plausible" Error Swallow | `fail_plausible_swallow` | `sev-2` | True |
| Ambiguous Timeout States | `ambiguous_timeout_duplicate` | `sev-1` | True |
| Tool-Call Retry Storms | `retry_storm_cascade` | `sev-1` | True |
| Doing Math in Prose | `math_in_prose` | `sev-3` | False |
| Session Context Contamination | `session_contamination` | `sev-2` | True |
| Goal Drift (Task Hijacking) | `goal_drift` | `sev-2` | False |
| Inter-Agent Trust Escalation | `inter_agent_trust_escalation` | `sev-1` | True |
| Reasoning-Action Mismatch | `reasoning_action_mismatch` | `sev-2` | False |
| Step Repetition (State Paralysis) | `state_paralysis_repetition` | `sev-2` | False |
| Premature Termination | `premature_termination` | `sev-3` | False |
| Stale Context Execution | `stale_context_execution` | `sev-2` | False |
| Information Withholding (Agent Silos) | `agent_silo_withholding` | `sev-3` | False |
| Agentic Supply Chain Compromise | `agentic_supply_chain` | `sev-1` | True |
| Unsafe Automation Brittleness | `unsafe_automation_brittleness` | `sev-1` | True |
| The Visual / UI Attack | `visual_ui_injection` | `sev-1` | True |

## Data Schema

Each record contains:
* `id`: Unique scenario identifier (e.g., `inc_retry_storm_cascade_01`)
* `pattern`: Canonical pattern tag
* `pattern_name`: Human-readable pattern name
* `scenario_title`: Real-world operational title
* `variation_axis`: Architecture / technology stack under test
* `input`:
  * `alert`: Alert name, threshold, firing duration
  * `logs`: Formatted telemetry logs at minute 5
  * `context`: Deploys, services, tables, agent state
* `gold_triage`: Fixed 5-key evaluation output:
  * `pattern` (string)
  * `root_cause` (string)
  * `severity` (`sev-1` \| `sev-2` \| `sev-3`)
  * `first_action` (actionable runbook step)
  * `escalate` (boolean)
* `messages`: SFT-ready prompt and completion
