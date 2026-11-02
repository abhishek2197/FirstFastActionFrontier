#!/usr/bin/env python3
"""
Evaluate Nemotron Lightning 3.5 30B (accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b)
on the Minute Five golden synthetic test cases.
"""

import os
import re
import sys
import json
import time
import math
import argparse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

def wilson_ci(successes, total):
    if total == 0:
        return 0.0, 0.0, 0.0
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z**2 / total
    centre_adj_p = (p + z**2 / (2 * total)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)) / denom
    return p * 100, max(0.0, centre_adj_p - margin) * 100, min(1.0, centre_adj_p + margin) * 100

ALLOWED_PATTERNS = [
    "fail_plausible_swallow",
    "ambiguous_timeout_duplicate",
    "retry_storm_cascade",
    "math_in_prose",
    "session_contamination",
    "goal_drift",
    "inter_agent_trust_escalation",
    "reasoning_action_mismatch",
    "state_paralysis_repetition",
    "premature_termination",
    "stale_context_execution",
    "agent_silo_withholding",
    "agentic_supply_chain",
    "unsafe_automation_brittleness",
    "visual_ui_injection"
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

def clean_json(text):
    if not text:
        return ""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text

def normalize_severity(sev):
    if not sev:
        return "unknown"
    s = str(sev).lower().strip()
    if "1" in s or "critical" in s or "p1" in s:
        return "sev-1"
    if "2" in s or "high" in s or "p2" in s:
        return "sev-2"
    if "3" in s or "medium" in s or "low" in s or "p3" in s:
        return "sev-3"
    return s

def match_pattern(pred_pattern, gold_pattern):
    if not pred_pattern:
        return False, False
    pred_clean = pred_pattern.lower().strip().replace("-", "_").replace(" ", "_")
    gold_clean = gold_pattern.lower().strip().replace("-", "_")
    exact = (pred_clean == gold_clean)
    
    # Fuzzy keyword matching
    keywords = gold_clean.split("_")
    matched_kw = sum(1 for kw in keywords if kw in pred_clean)
    fuzzy = exact or (matched_kw >= max(2, len(keywords) - 1))
    return exact, fuzzy

def evaluate_case(case, api_key, model_name="accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b"):
    case_id = case["id"]
    gold_triage = case["gold_triage"]
    gold_pattern = gold_triage["pattern"]
    gold_sev = normalize_severity(gold_triage["severity"])
    gold_esc = bool(gold_triage["escalate"])

    c_input = case["input"]
    user_prompt = f"[ALERT]\n{c_input.get('alert', '')}\n\n[LOGS]\n{c_input.get('logs', '')}\n\n[CONTEXT]\n{c_input.get('context', '')}"

    system_prompt = (
        "You are a senior site reliability engineer triaging production incidents at minute five.\n"
        "Analyze the provided alert, logs, and context, and return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        "  \"pattern\": \"<one of the valid pattern tags below>\",\n"
        "  \"root_cause\": \"<1-2 sentence root cause explanation>\",\n"
        "  \"severity\": \"sev-1 | sev-2 | sev-3\",\n"
        "  \"first_action\": \"<immediate runbook action at minute five>\",\n"
        "  \"escalate\": true | false\n"
        "}\n\n"
        "VALID PATTERN TAGS:\n"
        "- fail_plausible_swallow\n"
        "- ambiguous_timeout_duplicate\n"
        "- retry_storm_cascade\n"
        "- math_in_prose\n"
        "- session_contamination\n"
        "- goal_drift\n"
        "- inter_agent_trust_escalation\n"
        "- reasoning_action_mismatch\n"
        "- state_paralysis_repetition\n"
        "- premature_termination\n"
        "- stale_context_execution\n"
        "- agent_silo_withholding\n"
        "- agentic_supply_chain\n"
        "- unsafe_automation_brittleness\n"
        "- visual_ui_injection\n\n"
        "Do not include preamble or code fences. Output raw JSON only."
    )

    url = "https://api.fireworks.ai/inference/v1/chat/completions"
    payload = {
        "model": model_name,
        "max_tokens": 32768,
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

    t0 = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            choice = data["choices"][0]
            raw_content = choice["message"].get("content", "")
            reasoning = choice["message"].get("reasoning_content", "")
    except Exception as e:
        return {
            "id": case_id,
            "gold_pattern": gold_pattern,
            "error": str(e),
            "json_valid": False,
            "exact_pattern_match": False,
            "fuzzy_pattern_match": False,
            "severity_match": False,
            "escalate_match": False,
            "false_escalation": False,
            "missed_escalation": False,
            "latency": time.time() - t0
        }

    cleaned = clean_json(raw_content)
    parsed = None
    json_valid = False
    try:
        parsed = json.loads(cleaned)
        json_valid = isinstance(parsed, dict) and "pattern" in parsed
    except Exception:
        json_valid = False

    if not json_valid:
        return {
            "id": case_id,
            "scenario_title": case.get("scenario_title"),
            "gold_pattern": gold_pattern,
            "raw_output": raw_content,
            "json_valid": False,
            "exact_pattern_match": False,
            "fuzzy_pattern_match": False,
            "severity_match": False,
            "escalate_match": False,
            "false_escalation": False,
            "missed_escalation": False,
            "latency": elapsed,
            "reasoning_len": len(reasoning)
        }

    pred_pattern = parsed.get("pattern", "")
    exact_match, fuzzy_match = match_pattern(pred_pattern, gold_pattern)
    pred_sev = normalize_severity(parsed.get("severity"))
    sev_match = (pred_sev == gold_sev)
    pred_esc = bool(parsed.get("escalate"))
    esc_match = (pred_esc == gold_esc)
    false_esc = (not gold_esc and pred_esc)
    missed_esc = (gold_esc and not pred_esc)

    return {
        "id": case_id,
        "scenario_title": case.get("scenario_title"),
        "gold_pattern": gold_pattern,
        "pred_pattern": pred_pattern,
        "gold_severity": gold_sev,
        "pred_severity": pred_sev,
        "gold_escalate": gold_esc,
        "pred_escalate": pred_esc,
        "gold_root_cause": gold_triage.get("root_cause"),
        "pred_root_cause": parsed.get("root_cause"),
        "gold_action": gold_triage.get("first_action"),
        "pred_action": parsed.get("first_action"),
        "json_valid": True,
        "exact_pattern_match": exact_match,
        "fuzzy_pattern_match": fuzzy_match,
        "severity_match": sev_match,
        "escalate_match": esc_match,
        "false_escalation": false_esc,
        "missed_escalation": missed_esc,
        "latency": elapsed,
        "reasoning_len": len(reasoning)
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate Nemotron on synthetic test cases")
    parser.add_argument("--model", type=str, default="accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b", help="Model endpoint on Fireworks")
    parser.add_argument("--dataset", type=str, default="data/synthetic_test_cases_500.jsonl", help="Dataset path")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases to evaluate")
    parser.add_argument("--quick", action="store_true", help="Run 1 case per pattern (15 cases total)")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent worker threads")
    args = parser.parse_args()

    api_key = load_api_key()
    dataset_file = args.dataset
    if not os.path.exists(dataset_file):
        dataset_file = "data/synthetic_test_cases.jsonl"
    if not os.path.exists(dataset_file):
        print(f"Error: {dataset_file} not found.")
        sys.exit(1)

    all_cases = [json.loads(line) for line in open(dataset_file)]
    
    if args.quick:
        # Pick first case of each pattern
        seen = set()
        cases = []
        for c in all_cases:
            if c["pattern"] not in seen:
                seen.add(c["pattern"])
                cases.append(c)
        print(f"Quick mode: Selected 1 case per pattern ({len(cases)} cases total).")
    elif args.limit:
        cases = all_cases[:args.limit]
        print(f"Running on first {len(cases)} test cases.")
    else:
        cases = all_cases
        print(f"Running full evaluation on all {len(cases)} test cases with model {args.model}.")

    os.makedirs("eval_results", exist_ok=True)
    results = []
    t_start = time.time()

    is_ultra = "ultra" in args.model.lower()
    model_display_name = "Nemotron-3 Ultra NVFP4 (~120B+)" if is_ultra else "Nemotron Lightning 3.5 30B (Base)"
    out_prefix = "nemotron_ultra" if is_ultra else "nemotron"
    out_report_name = "NEMOTRON_ULTRA_REPORT.md" if is_ultra else "NEMOTRON_BASELINE_REPORT.md"

    print(f"Evaluating {model_display_name} with {args.workers} concurrent workers...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(evaluate_case, c, api_key, args.model): c for c in cases}
        completed = 0
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            status_icon = "✓" if res.get("exact_pattern_match") else ("~" if res.get("fuzzy_pattern_match") else "✗")
            print(f"[{completed}/{len(cases)}] {status_icon} Case: {res['id']} | Gold: {res['gold_pattern']} | Pred: {res.get('pred_pattern', 'N/A')} ({res['latency']:.1f}s)")

    # Compute overall statistics
    total = len(results)
    json_valid_cnt = sum(1 for r in results if r.get("json_valid"))
    exact_pat_cnt = sum(1 for r in results if r.get("exact_pattern_match"))
    fuzzy_pat_cnt = sum(1 for r in results if r.get("fuzzy_pattern_match"))
    sev_cnt = sum(1 for r in results if r.get("severity_match"))
    esc_cnt = sum(1 for r in results if r.get("escalate_match"))
    false_esc_cnt = sum(1 for r in results if r.get("false_escalation"))
    missed_esc_cnt = sum(1 for r in results if r.get("missed_escalation"))
    avg_latency = sum(r.get("latency", 0) for r in results) / max(1, total)

    print("\n" + "="*50)
    print(f"EVALUATION SUMMARY: {model_display_name}")
    print("="*50)
    print(f"Total Cases Evaluated:       {total}")
    print(f"JSON Validity Rate:          {json_valid_cnt}/{total} ({json_valid_cnt/total*100:.1f}%)")
    print(f"Exact Pattern Accuracy:      {exact_pat_cnt}/{total} ({exact_pat_cnt/total*100:.1f}%)")
    print(f"Fuzzy/Semantic Pattern Acc:  {fuzzy_pat_cnt}/{total} ({fuzzy_pat_cnt/total*100:.1f}%)")
    print(f"Severity Classification Acc: {sev_cnt}/{total} ({sev_cnt/total*100:.1f}%)")
    print(f"Escalation Decision Acc:     {esc_cnt}/{total} ({esc_cnt/total*100:.1f}%)")
    print(f"False Escalation Count:      {false_esc_cnt} (crying wolf)")
    print(f"Missed Escalation Count:     {missed_esc_cnt} (missed critical incident)")
    print(f"Average Latency per Case:    {avg_latency:.2f}s")
    print("="*50)

    # Save detailed JSONL
    out_jsonl = f"eval_results/{out_prefix}_eval_results.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Generate Markdown Summary Report
    out_md = f"eval_results/{out_report_name}"
    with open(out_md, "w", encoding="utf-8") as f:
        jv_p, jv_l, jv_u = wilson_ci(json_valid_cnt, total)
        ep_p, ep_l, ep_u = wilson_ci(exact_pat_cnt, total)
        fp_p, fp_l, fp_u = wilson_ci(fuzzy_pat_cnt, total)
        sv_p, sv_l, sv_u = wilson_ci(sev_cnt, total)
        es_p, es_l, es_u = wilson_ci(esc_cnt, total)
        fe_p, fe_l, fe_u = wilson_ci(false_esc_cnt, total)
        me_p, me_l, me_u = wilson_ci(missed_esc_cnt, total)

        f.write("# Evaluation Report: " + model_display_name + "\n\n")
        f.write(f"Evaluated on {total} synthetic test cases using Fireworks endpoint `{args.model}`.\n\n")
        f.write("## Overall Metrics (with 95% Wilson Confidence Intervals)\n\n")
        f.write("| Metric | Score | Percentage | 95% Confidence Interval |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| **JSON Validity** | {json_valid_cnt} / {total} | {jv_p:.1f}% | [{jv_l:.1f}% - {jv_u:.1f}%] |\n")
        f.write(f"| **Exact Pattern Match** | {exact_pat_cnt} / {total} | {ep_p:.1f}% | [{ep_l:.1f}% - {ep_u:.1f}%] |\n")
        f.write(f"| **Fuzzy / Semantic Pattern Match** | {fuzzy_pat_cnt} / {total} | {fp_p:.1f}% | [{fp_l:.1f}% - {fp_u:.1f}%] |\n")
        f.write(f"| **Severity Accuracy** | {sev_cnt} / {total} | {sv_p:.1f}% | [{sv_l:.1f}% - {sv_u:.1f}%] |\n")
        f.write(f"| **Escalation Accuracy** | {esc_cnt} / {total} | {es_p:.1f}% | [{es_l:.1f}% - {es_u:.1f}%] |\n")
        f.write(f"| **False Escalation Rate** | {false_esc_cnt} cases | {fe_p:.1f}% | [{fe_l:.1f}% - {fe_u:.1f}%] |\n")
        f.write(f"| **Missed Escalation Rate** | {missed_esc_cnt} cases | {me_p:.1f}% | [{me_l:.1f}% - {me_u:.1f}%] |\n")
        f.write(f"| **Average Latency** | {avg_latency:.2f}s | - | - |\n\n")

        f.write("## Per-Case Breakdown\n\n")
        f.write("| Case ID | Gold Pattern | Pred Pattern | Match | Gold Sev | Pred Sev | Escalate Match |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in sorted(results, key=lambda x: x["id"]):
            match_str = "Exact" if r.get("exact_pattern_match") else ("Fuzzy" if r.get("fuzzy_pattern_match") else "Miss")
            f.write(f"| `{r['id']}` | `{r.get('gold_pattern')}` | `{r.get('pred_pattern', 'N/A')}` | {match_str} | {r.get('gold_severity')} | {r.get('pred_severity')} | {r.get('escalate_match')} |\n")

    print(f"\nDetailed results saved to {out_jsonl}")
    print(f"Markdown report saved to {out_md}")

if __name__ == "__main__":
    main()
