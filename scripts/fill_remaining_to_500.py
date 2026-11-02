#!/usr/bin/env python3
"""
Fills the remaining cases in data/synthetic_test_cases_500.jsonl to reach exactly 500 cases
using accounts/fireworks/models/glm-5p3 with concise reasoning control (2 cases per request).
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

sys.path.insert(0, os.path.abspath("."))
from scripts.expand_dataset_to_500 import PATTERNS, ARCH_BATCHES, clean_json_text, normalize_severity, load_api_key

def generate_mini_batch(pattern_info, arch_focus, num_needed, start_idx, api_key):
    name = pattern_info["name"]
    tag = pattern_info["tag"]
    rc = pattern_info["root_cause"]
    def_sev = pattern_info["default_severity"]
    def_esc = pattern_info["default_escalate"]
    desc = pattern_info["description"]

    system_prompt = (
        "You are an expert SRE Architect generating high-fidelity production incident datasets. "
        "Keep internal reasoning very concise (under 200 tokens). Output strictly valid JSON."
    )

    user_prompt = f"""Generate exactly {num_needed} distinct, high-fidelity production incident triage scenarios for:

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
        "max_tokens": 16384,
        "temperature": 0.2,
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
                choice = res_data["choices"][0]
                content = choice["message"].get("content")
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
    jsonl_path = "data/synthetic_test_cases_500.jsonl"
    json_path = "data/synthetic_test_cases_500.json"
    train_sft_path = "data/train_sft.jsonl"

    all_cases = []
    if os.path.exists(jsonl_path):
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
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

        curr_offset = current_cnt
        b_idx = 0
        while needed > 0:
            take = min(2, needed)  # 2 cases per call to keep reasoning brief and prevent timeouts
            arch = ARCH_BATCHES[b_idx % len(ARCH_BATCHES)]
            tasks.append((p, arch, take, curr_offset))
            curr_offset += take
            needed -= take
            b_idx += 1

    print(f"Total remaining tasks: {len(tasks)} (requesting {sum(t[2] for t in tasks)} cases to reach 500 with GLM-5.3)...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(generate_mini_batch, p, arch, take, off, api_key): (p["tag"], take)
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

    final_cases = all_cases[:500]
    print(f"\nFinal dataset size: {len(final_cases)} test cases.")

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for c in final_cases:
            f.write(json.dumps(c) + "\n")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(final_cases, f, indent=2)

    with open(train_sft_path, "w", encoding="utf-8") as f:
        for c in final_cases:
            f.write(json.dumps({"messages": c["messages"]}) + "\n")

    elapsed = time.time() - start_time
    print(f"Done in {elapsed:.1f}s! Saved {len(final_cases)} cases to {jsonl_path}.")

if __name__ == "__main__":
    main()
