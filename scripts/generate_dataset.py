#!/usr/bin/env python3
"""
Generate 5 synthetic test cases per failure pattern (75 cases total)
using Fireworks API (accounts/fireworks/models/glm-5p3).
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

PATTERNS = [
    {
        "tag": "fail_plausible_swallow",
        "name": "The Fail-Plausible Error Swallow",
        "root_cause": "Error swallowing and chained hallucination",
        "default_severity": "sev-2",
        "default_escalate": True,
        "description": "Agent encounters underlying system error (500, DB timeout, permissions). Instead of escalating or surfacing the error, it incorporates it into fluent, plausible prose claiming empty results, zero records, or successful clearance."
    },
    {
        "tag": "ambiguous_timeout_duplicate",
        "name": "Ambiguous Timeout States (Duplicate Action)",
        "root_cause": "Non-idempotent tool calls lacking state verification",
        "default_severity": "sev-1",
        "default_escalate": True,
        "description": "Agent makes a stateful external mutation (charges, tickets, provisioning). The API executes successfully but the connection times out before 200 OK is received. Agent retries without idempotency key, causing double executions."
    },
    {
        "tag": "retry_storm_cascade",
        "name": "Tool-Call Retry Storms",
        "root_cause": "Missing circuit breakers and recursive turn retries",
        "default_severity": "sev-1",
        "default_escalate": True,
        "description": "Tool call fails. Naive retry logic causes the framework to re-run full LLM turns rather than simple HTTP backoff, causing massive token spend spikes, context window bloat, and API rate-limiting."
    },
    {
        "tag": "math_in_prose",
        "name": "Doing Math in Prose",
        "root_cause": "Calculation hallucination / improper tool delegation",
        "default_severity": "sev-3",
        "default_escalate": False,
        "description": "Agent queries accurate raw data via SQL or API, but calculates aggregations, margins, or percentages inside its free-form text reasoning tokens rather than using Python/calculator tool, outputting confident arithmetic errors."
    },
    {
        "tag": "session_contamination",
        "name": "Session Context Contamination",
        "root_cause": "Weak boundary between trusted prompt and untrusted data",
        "default_severity": "sev-2",
        "default_escalate": True,
        "description": "Agent ingests untrusted or adversarial user data early in a session. This contaminated text leaks across multi-turn memory or shared session context, altering system behavior in subsequent tasks without triggering safety tripwires."
    },
    {
        "tag": "goal_drift",
        "name": "Goal Drift (Task Hijacking)",
        "root_cause": "Shallow memory and context window attention decay",
        "default_severity": "sev-2",
        "default_escalate": False,
        "description": "Agent given a multi-step objective gets distracted mid-execution by a noisy log warning or tangential edge-case result, abandoning the primary user goal and burning compute resolving irrelevant sub-tasks."
    },
    {
        "tag": "inter_agent_trust_escalation",
        "name": "Inter-Agent Trust Escalation",
        "root_cause": "Positional trust instead of cryptographic identity verification",
        "default_severity": "sev-1",
        "default_escalate": True,
        "description": "Orchestrator agent delegates task to sub-agent. Sub-agent requests elevated admin privileges or sensitive credentials via natural language; orchestrator grants them without cryptographic authorization verification."
    },
    {
        "tag": "reasoning_action_mismatch",
        "name": "Reasoning-Action Mismatch",
        "root_cause": "Attention failure between reasoning tokens and generation tokens",
        "default_severity": "sev-2",
        "default_escalate": False,
        "description": "Agent chain-of-thought explicitly deduces that an action is dangerous or incorrect (e.g., abort rollback to prevent data loss), but the actual tool call JSON executes the forbidden action."
    },
    {
        "tag": "state_paralysis_repetition",
        "name": "Step Repetition (State Paralysis)",
        "root_cause": "State persistence failure or stale knowledge retrieval",
        "default_severity": "sev-2",
        "default_escalate": False,
        "description": "Agent completes a tool call successfully, but environment latency or internal scratchpad failure means state does not update immediately. Agent executes the identical tool call in an infinite loop."
    },
    {
        "tag": "premature_termination",
        "name": "Premature Termination",
        "root_cause": "Flawed stop heuristics / misjudged completion criteria",
        "default_severity": "sev-3",
        "default_escalate": False,
        "description": "Given a batch of items (e.g. 5 tables to verify or 10 files to process), agent finishes item 1, outputs partial summary, and halts prematurely with finish_reason stop, leaving majority of task undone."
    },
    {
        "tag": "stale_context_execution",
        "name": "Stale Context Execution",
        "root_cause": "Vector DB / Knowledge Base sync lag",
        "default_severity": "sev-2",
        "default_escalate": False,
        "description": "RAG pipeline retrieves outdated runbook or deprecated API schema. Agent confidently executes an obsolete deployment or configuration procedure that breaks in the current environment."
    },
    {
        "tag": "agent_silo_withholding",
        "name": "Information Withholding (Agent Silos)",
        "root_cause": "Unstructured or unenforced inter-agent payload schemas",
        "default_severity": "sev-3",
        "default_escalate": False,
        "description": "Research agent identifies critical environmental constraint (e.g., specific VPC or region restriction), but omits it during serialized handoff to downstream execution agent, causing downstream execution failure."
    },
    {
        "tag": "agentic_supply_chain",
        "name": "Agentic Supply Chain Compromise",
        "root_cause": "Treating natural-language tool descriptions as documentation rather than executable code",
        "default_severity": "sev-1",
        "default_escalate": True,
        "description": "Agent loads third-party MCP tool definition or prompt template containing prompt injection directing data exfiltration or unauthorized system modifications."
    },
    {
        "tag": "unsafe_automation_brittleness",
        "name": "Unsafe Automation Brittleness",
        "root_cause": "Missing pre-execution human-in-the-loop (HITL) gates",
        "default_severity": "sev-1",
        "default_escalate": True,
        "description": "Agent generates valid plan but bypasses human approval gates for high-blast-radius destructive action (dropping production table, terminating cluster, revoking certificates) under noisy alert conditions."
    },
    {
        "tag": "visual_ui_injection",
        "name": "The Visual / UI Attack",
        "root_cause": "Multi-modal agents prioritizing hidden visual cues over system instructions",
        "default_severity": "sev-1",
        "default_escalate": True,
        "description": "Computer Use Agent (CUA) views web page or UI screenshot with hidden/low-contrast prompt injection text, causing it to deviate from user task and execute unauthorized browsing or data transfer."
    }
]

def load_api_key():
    key = os.environ.get("FIREWORKS_API_KEY")
    if key:
        return key.strip().strip('"')
    if os.path.exists(".env"):
        for line in open(".env"):
            if line.startswith("FIREWORKS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    raise ValueError("FIREWORKS_API_KEY not found in env or .env file")

def clean_json_text(text):
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
    # Find outer bracket or brace
    start_bracket = text.find('[')
    start_brace = text.find('{')
    if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
        end_bracket = text.rfind(']')
        if end_bracket != -1:
            text = text[start_bracket:end_bracket+1]
    elif start_brace != -1:
        end_brace = text.rfind('}')
        if end_brace != -1:
            text = text[start_brace:end_brace+1]
    return text

def normalize_severity(sev):
    s = str(sev).lower()
    if "1" in s or "critical" in s or "p1" in s:
        return "sev-1"
    if "2" in s or "high" in s or "p2" in s:
        return "sev-2"
    return "sev-3"

def generate_cases_for_pattern(pattern_info, api_key, max_retries=3):
    tag = pattern_info["tag"]
    name = pattern_info["name"]
    desc = pattern_info["description"]
    rc = pattern_info["root_cause"]
    def_sev = pattern_info["default_severity"]
    def_esc = pattern_info["default_escalate"]

    system_prompt = (
        "You are an expert site reliability and AI agent systems engineer creating synthetic "
        "benchmark test cases for production incident triage at Minute Five. "
        "Keep your internal reasoning very concise. You must return ONLY a valid JSON array of objects."
    )

    user_prompt = f"""Generate exactly 5 distinct, highly realistic production incident test cases for the following failure pattern:

Pattern: {name}
Tag: {tag}
Primary Root Cause: {rc}
Description: {desc}
Baseline Severity: {def_sev}
Escalate Default: {def_esc}

REQUIREMENTS FOR EACH OF THE 5 TEST CASES:
1. Scenario must represent a realistic production telemetry snapshot at MINUTE FIVE (alert fired 5 min ago; root cause is not stated verbatim in the alert, but is deducible from the symptoms).
2. Telemetry must vary across different real-world architectures (e.g. Kubernetes, Databricks, Kafka, Snowflake, LangChain/CrewAI orchestrators, Stripe/AWS/Salesforce APIs).
3. Include near-miss nuance (one case should have noisy red-herring logs that test discrimination).
4. Strictly return a JSON array containing 5 objects with this structure:
[
  {{
    "scenario_title": "Descriptive title of incident",
    "variation_axis": "e.g., Kafka microbatching / Redis caching / MCP plugin",
    "input": {{
      "alert": "Exact monitoring alert name, threshold, and metrics at min 5",
      "logs": "Realistic excerpt of 4-8 log lines at min 5 showing symptoms",
      "context": "Recent deploys, affected services/tables, active agent tasks"
    }},
    "gold_triage": {{
      "pattern": "{tag}",
      "root_cause": "Clear 1-2 sentence explanation of the underlying root cause",
      "severity": "{def_sev}",
      "first_action": "Specific concrete remediation step for on-call engineer at minute 5",
      "escalate": {json.dumps(def_esc)}
    }}
  }}
]
Output ONLY raw JSON."""

    url = "https://api.fireworks.ai/inference/v1/chat/completions"
    payload = {
        "model": "accounts/fireworks/models/glm-5p3",
        "max_tokens": 8192,
        "top_k": 40,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=90) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                choice = res_data["choices"][0]
                content = choice["message"].get("content")
                if not content:
                    print(f"[{tag}] Attempt {attempt+1}: Empty content, retrying...")
                    time.sleep(2)
                    continue
                
                cleaned = clean_json_text(content)
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and "test_cases" in parsed:
                    parsed = parsed["test_cases"]
                if not isinstance(parsed, list):
                    parsed = [parsed]
                
                # Format cases
                results = []
                for idx, item in enumerate(parsed[:5]):
                    c_input = item.get("input", {})
                    if isinstance(c_input.get("logs"), list):
                        c_input["logs"] = "\n".join(c_input["logs"])
                    if isinstance(c_input.get("context"), dict):
                        c_input["context"] = "\n".join([f"{k}: {v}" for k, v in c_input["context"].items()])
                    
                    gt = item.get("gold_triage", {})
                    gt["pattern"] = tag
                    gt["severity"] = normalize_severity(gt.get("severity", def_sev))
                    gt["escalate"] = bool(gt.get("escalate", def_esc))
                    if not gt.get("root_cause"):
                        gt["root_cause"] = rc
                    if not gt.get("first_action"):
                        gt["first_action"] = "Quarantine affected agent process and investigate telemetry logs"
                    
                    user_msg_content = f"[ALERT]\n{c_input.get('alert', '')}\n\n[LOGS]\n{c_input.get('logs', '')}\n\n[CONTEXT]\n{c_input.get('context', '')}"
                    assistant_msg_content = json.dumps(gt, indent=2)

                    formatted_case = {
                        "id": f"inc_{tag}_{idx+1:02d}",
                        "pattern": tag,
                        "pattern_name": name,
                        "scenario_title": item.get("scenario_title", f"{name} incident #{idx+1}"),
                        "variation_axis": item.get("variation_axis", "Default architecture"),
                        "input": c_input,
                        "gold_triage": gt,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a senior site reliability engineer triaging production incidents at minute five. Return only structured JSON with keys: pattern, root_cause, severity, first_action, escalate."
                            },
                            {
                                "role": "user",
                                "content": user_msg_content
                            },
                            {
                                "role": "assistant",
                                "content": assistant_msg_content
                            }
                        ]
                    }
                    results.append(formatted_case)
                
                if len(results) >= 5:
                    print(f"[{tag}] Successfully generated 5 test cases.")
                    return results[:5]
                elif len(results) > 0:
                    print(f"[{tag}] Generated {len(results)} cases (needed 5), attempting supplement...")
                    return results
        except Exception as e:
            print(f"[{tag}] Attempt {attempt+1} error: {e}")
            time.sleep(3)

    print(f"[{tag}] Failed to generate cases after {max_retries} attempts.")
    return []

def main():
    api_key = load_api_key()
    os.makedirs("data", exist_ok=True)
    all_cases = []

    print(f"Starting generation of 5 test cases per pattern across {len(PATTERNS)} patterns (target: 75 cases)...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_pattern = {
            executor.submit(generate_cases_for_pattern, p, api_key): p for p in PATTERNS
        }
        for future in as_completed(future_to_pattern):
            pattern = future_to_pattern[future]
            try:
                cases = future.result()
                all_cases.extend(cases)
                print(f"Progress: {len(all_cases)}/75 cases generated so far...")
            except Exception as e:
                print(f"Pattern {pattern['tag']} generation exception: {e}")

    # Save to data/synthetic_test_cases.json and .jsonl
    jsonl_path = "data/synthetic_test_cases.jsonl"
    json_path = "data/synthetic_test_cases.json"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in all_cases:
            f.write(json.dumps(c) + "\n")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, indent=2)

    elapsed = time.time() - start_time
    print(f"\nDone! Generated {len(all_cases)} test cases in {elapsed:.1f}s.")
    print(f"Saved to {jsonl_path} and {json_path}.")

if __name__ == "__main__":
    main()
