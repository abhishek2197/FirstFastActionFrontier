#!/usr/bin/env python3
"""
Evaluate the First Fast Action Frontier Compound Speculative Router
against the golden synthetic test cases.
"""

import os
import sys
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.abspath("."))
from src.router import SpeculativeTriageRouter
from scripts.evaluate_nemotron import normalize_severity, match_pattern, load_api_key, wilson_ci

def evaluate_case_harness(case, router):
    case_id = case["id"]
    gold_triage = case["gold_triage"]
    gold_pattern = gold_triage["pattern"]
    gold_sev = normalize_severity(gold_triage["severity"])
    gold_esc = bool(gold_triage["escalate"])

    c_input = case["input"]
    alert = c_input.get("alert", "")
    logs = c_input.get("logs", "")
    context = c_input.get("context", "")

    start_time = time.time()
    try:
        res = router.triage_incident(alert=alert, logs=logs, context=context)
        elapsed = res.get("latency_sec", time.time() - start_time)
        triage = res.get("triage", {})
        if not isinstance(triage, dict):
            triage = {}

        pred_pattern = triage.get("pattern", "")
        pred_sev = normalize_severity(triage.get("severity", ""))
        pred_esc = triage.get("escalate")

        exact_match, fuzzy_match = match_pattern(pred_pattern, gold_pattern)
        sev_match = (pred_sev == gold_sev)
        esc_match = (pred_esc == gold_esc)
        false_esc = (pred_esc is True and gold_esc is False)
        missed_esc = (pred_esc is False and gold_esc is True)

        return {
            "id": case_id,
            "gold_pattern": gold_pattern,
            "pred_pattern": pred_pattern,
            "exact_pattern_match": exact_match,
            "fuzzy_pattern_match": fuzzy_match,
            "gold_severity": gold_sev,
            "pred_severity": pred_sev,
            "severity_match": sev_match,
            "gold_escalate": gold_esc,
            "pred_escalate": pred_esc,
            "escalate_match": esc_match,
            "false_escalation": false_esc,
            "missed_escalation": missed_esc,
            "latency": elapsed,
            "route_taken": res.get("route_taken"),
            "escalated": res.get("escalated"),
            "cost_estimate_usd": res.get("cost_estimate_usd"),
            "json_valid": True
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "id": case_id,
            "gold_pattern": gold_pattern,
            "pred_pattern": "ERROR",
            "exact_pattern_match": False,
            "fuzzy_pattern_match": False,
            "gold_severity": gold_sev,
            "pred_severity": "unknown",
            "severity_match": False,
            "gold_escalate": gold_esc,
            "pred_escalate": None,
            "escalate_match": False,
            "false_escalation": False,
            "missed_escalation": False,
            "latency": elapsed,
            "route_taken": "error",
            "escalated": False,
            "cost_estimate_usd": 0.0,
            "json_valid": False,
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Evaluate Compound Speculative Router")
    parser.add_argument("--dataset", type=str, default="data/synthetic_test_cases_500.jsonl", help="Dataset path")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases")
    parser.add_argument("--quick", action="store_true", help="Run 1 case per pattern (15 cases total)")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers")
    args = parser.parse_args()

    api_key = load_api_key()
    router = SpeculativeTriageRouter(api_key=api_key)

    dataset_file = args.dataset
    if not os.path.exists(dataset_file):
        dataset_file = "data/synthetic_test_cases_500.jsonl"

    all_cases = [json.loads(line) for line in open(dataset_file)]

    if args.quick:
        seen = set()
        cases = []
        for c in all_cases:
            if c["pattern"] not in seen:
                seen.add(c["pattern"])
                cases.append(c)
        print(f"Quick mode: Evaluating First Fast Action Frontier on 1 case per pattern ({len(cases)} cases total)...")
    elif args.limit:
        cases = all_cases[:args.limit]
        print(f"Running on first {len(cases)} cases...")
    else:
        cases = all_cases
        print(f"Running full evaluation on all {len(cases)} cases...")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(evaluate_case_harness, c, router): c for c in cases}
        completed = 0
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            completed += 1
            status_icon = "✓" if res.get("exact_pattern_match") else "✗"
            print(f"[{completed}/{len(cases)}] {status_icon} Case: {res['id']} | Gold: {res['gold_pattern']} | Pred: {res.get('pred_pattern', 'N/A')} | Route: {res.get('route_taken')} ({res['latency']:.1f}s)")

    total = len(results)
    exact_cnt = sum(1 for r in results if r.get("exact_pattern_match"))
    json_valid_cnt = sum(1 for r in results if r.get("json_valid"))
    fast_path_cnt = sum(1 for r in results if not r.get("escalated"))
    avg_lat = sum(r.get("latency", 0) for r in results) / max(1, total)

    ep_p, ep_l, ep_u = wilson_ci(exact_cnt, total)
    jv_p, jv_l, jv_u = wilson_ci(json_valid_cnt, total)

    print("\n" + "="*50)
    print("EVALUATION SUMMARY: First Fast Action Frontier (Harness)")
    print("="*50)
    print(f"Total Cases Evaluated:       {total}")
    print(f"Exact Pattern Accuracy:      {exact_cnt}/{total} ({ep_p:.1f}%) [95% CI: {ep_l:.1f}% - {ep_u:.1f}%]")
    print(f"JSON Validity:               {json_valid_cnt}/{total} ({jv_p:.1f}%) [95% CI: {jv_l:.1f}% - {jv_u:.1f}%]")
    print(f"Fast-Path Speculative Rate:  {fast_path_cnt}/{total} ({fast_path_cnt/total*100:.1f}%)")
    print(f"Average Latency:             {avg_lat:.2f}s")
    print("="*50)

    # Save detailed JSONL & MD
    out_jsonl = "eval_results/harness_eval_results.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    out_md = "eval_results/HARNESS_EVALUATION_REPORT.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Evaluation Report: First Fast Action Frontier (Speculative Harness)\n\n")
        f.write(f"Evaluated on {total} test cases using compound speculative harness.\n\n")
        f.write("## Overall Metrics (95% Wilson Confidence Intervals)\n\n")
        f.write("| Metric | Score | Percentage | 95% Confidence Interval |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| **Exact Pattern Match** | {exact_cnt} / {total} | {ep_p:.1f}% | [{ep_l:.1f}% - {ep_u:.1f}%] |\n")
        f.write(f"| **JSON Validity** | {json_valid_cnt} / {total} | {jv_p:.1f}% | [{jv_l:.1f}% - {jv_u:.1f}%] |\n")
        f.write(f"| **Fast Speculative Path (<1s)** | {fast_path_cnt} / {total} | {fast_path_cnt/total*100:.1f}% | - |\n")
        f.write(f"| **Average Latency** | {avg_lat:.2f}s | - | - |\n")

    print(f"\nDetailed report saved to {out_md}")

if __name__ == "__main__":
    main()
