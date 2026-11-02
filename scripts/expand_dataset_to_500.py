#!/usr/bin/env python3
"""
Expand synthetic test cases dataset from 75 to 500 examples (stratified across 15 patterns)
using Fireworks API (accounts/fireworks/models/glm-5p3).
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

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

ARCH_BATCHES = [
    "Cloud Native & Kubernetes Infrastructure (EKS, GKE, Envoy proxy, CoreDNS, Istio mesh, Cilium, Helm deploys)",
    "Data & Streaming Platforms (Apache Kafka, Apache Spark, Flink, Snowflake, Databricks Delta Lake, BigQuery)",
    "Autonomous Agent Frameworks (LangChain ReAct agents, CrewAI, AutoGen, Model Context Protocol MCP servers, FastMCP)",
    "Enterprise Backends & Microservices (PostgreSQL, MongoDB, Redis clusters, Stripe payments, Salesforce API, Celery queues)"
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

def normalize_severity(sev, def_sev):
    if not sev:
        return def_sev
    s = str(sev).lower().strip()
    if "1" in s or "critical" in s or "p1" in s:
        return "sev-1"
    if "2" in s or "high" in s or "p2" in s:
        return "sev-2"
    if "3" in s or "medium" in s or "low" in s or "p3" in s:
        return "sev-3"
    return def_sev

def generate_sub_batch(pattern_info, arch_focus, num_needed, start_idx, api_key):
    tag = pattern_info["tag"]
    name = pattern_info["name"]
    desc = pattern_info["description"]
    rc = pattern_info["root_cause"]
    def_sev = pattern_info["default_severity"]
    def_esc = pattern_info["default_escalate"]

    system_prompt = (
        "You are an expert site reliability and AI agent systems engineer creating synthetic "
        "benchmark test cases for production incident triage at Minute Five. "
        "Keep your internal reasoning concise. Output ONLY a valid JSON array of objects."
    )

    user_prompt = f"""Generate exactly {num_needed} distinct, production incident test cases for the failure pattern below:

Pattern: {name} (Tag: {tag})
Root Cause: {rc}
Description: {desc}
Architectural Domain Focus: {arch_focus}

Requirements for each case at MINUTE FIVE:
- Realistic monitoring alert text
- 4-8 lines of realistic telemetry/log excerpt at minute 5
- Relevant context (service, recent deploy, affected shards/tables)
- Output MUST be a valid JSON array of {num_needed} objects:
[
  {{
    "scenario_title": "...",
    "variation_axis": "...",
    "input": {{"alert": "...", "logs": "...", "context": "..."}},
    "gold_triage": {{
      "pattern": "{tag}",
      "root_cause": "...",
      "severity": "{def_sev}",
      "first_action": "...",
      "escalate": {json.dumps(def_esc)}
    }}
  }}
]"""

    url = "https://api.fireworks.ai/inference/v1/chat/completions"
    payload = {
        "model": "accounts/fireworks/models/glm-5p3",
        "max_tokens": 8192,
        "top_k": 40,
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

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=90) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                content = res_data["choices"][0]["message"].get("content")
                if not content:
                    time.sleep(2)
                    continue

                cleaned = clean_json_text(content)
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and "test_cases" in parsed:
                    parsed = parsed["test_cases"]
                if not isinstance(parsed, list):
                    parsed = [parsed]

                formatted = []
                for idx, item in enumerate(parsed[:num_needed]):
                    c_input = item.get("input", {})
                    if isinstance(c_input.get("logs"), list):
                        c_input["logs"] = "\n".join(c_input["logs"])
                    if isinstance(c_input.get("context"), dict):
                        c_input["context"] = "\n".join([f"{k}: {v}" for k, v in c_input["context"].items()])

                    gt = item.get("gold_triage", {})
                    gt["pattern"] = tag
                    gt["severity"] = normalize_severity(gt.get("severity"), def_sev)
                    gt["escalate"] = bool(gt.get("escalate", def_esc))
                    if not gt.get("root_cause"):
                        gt["root_cause"] = rc
                    if not gt.get("first_action"):
                        gt["first_action"] = "Quarantine affected agent process and investigate telemetry logs"

                    user_msg = f"[ALERT]\n{c_input.get('alert', '')}\n\n[LOGS]\n{c_input.get('logs', '')}\n\n[CONTEXT]\n{c_input.get('context', '')}"
                    case_num = start_idx + idx + 1
                    formatted_case = {
                        "id": f"inc_{tag}_{case_num:02d}",
                        "pattern": tag,
                        "pattern_name": name,
                        "scenario_title": item.get("scenario_title", f"{name} incident #{case_num}"),
                        "variation_axis": item.get("variation_axis", arch_focus),
                        "input": c_input,
                        "gold_triage": gt,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a senior site reliability engineer triaging production incidents at minute five. Return only structured JSON with keys: pattern, root_cause, severity, first_action, escalate."
                            },
                            {
                                "role": "user",
                                "content": user_msg
                            },
                            {
                                "role": "assistant",
                                "content": json.dumps(gt, indent=2)
                            }
                        ]
                    }
                    formatted.append(formatted_case)
                return formatted
        except Exception as e:
            time.sleep(2)

    return []

def main():
    api_key = load_api_key()
    existing_file = "data/synthetic_test_cases.jsonl"
    all_cases = []

    if os.path.exists(existing_file):
        for line in open(existing_file):
            all_cases.append(json.loads(line))
        print(f"Loaded {len(all_cases)} existing test cases.")

    pattern_counts = defaultdict(int)
    for c in all_cases:
        pattern_counts[c["pattern"]] += 1

    TARGET_PER_PATTERN = 34  # 34 * 10 + 33 * 5 = 505 -> trimmed to exactly 500
    tasks = []

    for p in PATTERNS:
        current_cnt = pattern_counts[p["tag"]]
        needed = max(0, TARGET_PER_PATTERN - current_cnt)
        if needed <= 0:
            continue
        
        # Divide needed cases across 4 architectural focus areas
        chunk_size = 7
        curr_offset = current_cnt
        for b_idx in range(4):
            take = min(chunk_size, needed)
            if take <= 0:
                break
            tasks.append((p, ARCH_BATCHES[b_idx], take, curr_offset))
            curr_offset += take
            needed -= take

    print(f"Total generation tasks: {len(tasks)} (concurrently requesting {sum(t[2] for t in tasks)} new cases to reach 500)...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(generate_sub_batch, p, arch, take, off, api_key): (p["tag"], take)
            for (p, arch, take, off) in tasks
        }
        for future in as_completed(futures):
            tag, take = futures[future]
            try:
                new_cases = future.result()
                all_cases.extend(new_cases)
                print(f"[{tag}] +{len(new_cases)} cases (Total: {len(all_cases)}/500)")
            except Exception as e:
                print(f"[{tag}] Error: {e}")

    # Trim or ensure exactly 500
    final_cases = all_cases[:500]
    print(f"\nFinal dataset size: {len(final_cases)} test cases.")

    # Save to JSONL and JSON
    jsonl_path = "data/synthetic_test_cases_500.jsonl"
    json_path = "data/synthetic_test_cases_500.json"
    train_sft_path = "data/train_sft.jsonl"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in final_cases:
            f.write(json.dumps(c) + "\n")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_cases, f, indent=2)

    with open(train_sft_path, "w", encoding="utf-8") as f:
        for c in final_cases:
            f.write(json.dumps({"messages": c["messages"]}) + "\n")

    elapsed = time.time() - start_time
    print(f"Done in {elapsed:.1f}s!")
    print(f"Saved {len(final_cases)} cases to {jsonl_path}, {json_path}, and {train_sft_path}.")

if __name__ == "__main__":
    main()
