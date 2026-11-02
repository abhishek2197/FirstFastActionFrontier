#!/usr/bin/env python3
"""
Evaluate Muse Glimmer 30B (accounts/fireworks/models/muse-glimmer-30b)
on the held-out evaluation test cases using Fireworks Serverless Sampling API.
"""

import os
import re
import sys
import json
import time
import math
import argparse
from pathlib import Path

# Add cookbook directory to sys.path so training.* packages import cleanly
COOKBOOK_DIR = Path(__file__).resolve().parent.parent / ".cookbook" / "training"
if str(COOKBOOK_DIR.parent) not in sys.path:
    sys.path.insert(0, str(COOKBOOK_DIR.parent))

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(usecwd=True))

from fireworks.training.sdk import FiretitanServiceClient
from training.renderer.tokenizer import get_tokenizer
from training.renderer import get_renderer, get_text_content
from fireworks.training import sdk

def wilson_ci(successes, total):
    if total == 0:
        return 0.0, 0.0, 0.0
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z**2 / total
    centre_adj_p = (p + z**2 / (2 * total)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)) / denom
    return p * 100, max(0.0, centre_adj_p - margin) * 100, min(1.0, centre_adj_p + margin) * 100

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
    keywords = gold_clean.split("_")
    matched_kw = sum(1 for kw in keywords if kw in pred_clean)
    fuzzy = exact or (matched_kw >= max(2, len(keywords) - 1))
    return exact, fuzzy

def parse_case(row):
    """Handles both raw chat messages format and synthetic test case schema."""
    if "messages" in row:
        msgs = row["messages"]
        user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
        asst_msg = next((m["content"] for m in msgs if m["role"] == "assistant"), "{}")
        gold = json.loads(clean_json(asst_msg))
        return {
            "id": row.get("id", f"case-{hash(user_msg)%100000:05d}"),
            "user_prompt": user_msg,
            "gold_pattern": gold.get("pattern", "unknown"),
            "gold_severity": normalize_severity(gold.get("severity", "unknown")),
            "gold_escalate": bool(gold.get("escalate", False)),
            "gold_raw": gold
        }
    else:
        c_input = row.get("input", {})
        user_prompt = f"[ALERT]\n{c_input.get('alert', '')}\n\n[LOGS]\n{c_input.get('logs', '')}\n\n[CONTEXT]\n{c_input.get('context', '')}"
        gt = row.get("gold_triage", {})
        return {
            "id": row.get("id", "case-unknown"),
            "user_prompt": user_prompt,
            "gold_pattern": gt.get("pattern", "unknown"),
            "gold_severity": normalize_severity(gt.get("severity", "unknown")),
            "gold_escalate": bool(gt.get("escalate", False)),
            "gold_raw": gt
        }

def main():
    parser = argparse.ArgumentParser(description="Evaluate Muse Glimmer 30B on held-out evaluation cases")
    parser.add_argument("--model", type=str, default="accounts/fireworks/models/muse-glimmer-30b", help="Model endpoint")
    parser.add_argument("--dataset", type=str, default="data/eval_split_100.jsonl", help="Dataset file path")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch submission size")
    args = parser.parse_args()

    api_key = os.environ.get("FIREWORKS_API_KEY")
    if not api_key:
        raise ValueError("FIREWORKS_API_KEY not found in environment or .env")

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        sys.exit(f"Dataset {dataset_path} does not exist.")

    raw_rows = [json.loads(line) for line in dataset_path.read_text().splitlines() if line.strip()]
    if args.limit:
        raw_rows = raw_rows[:args.limit]
    cases = [parse_case(r) for r in raw_rows]

    print(f"Loaded {len(cases)} test cases from {dataset_path}")
    print(f"Initializing tokenizer and renderer for Muse Glimmer 30B...")
    tok = get_tokenizer("meta-models/Muse-Glimmer-30B")
    renderer = get_renderer("muse_glimmer", tok)

    service = FiretitanServiceClient(
        api_key=api_key,
        base_url="https://api.fireworks.ai/training/v1/serverless"
    )

    print(f"Connecting to Serverless Sampling Client ({args.model})...")
    sampler = service.create_sampling_client(base_model=args.model, tokenizer=tok)
    params = sdk.SamplingParams(max_tokens=512, temperature=0.0, stop=renderer.get_stop_sequences())

    results = []
    t_start = time.time()

    print(f"\nRunning evaluation on {len(cases)} cases...")
    for idx, c in enumerate(cases):
        t0 = time.time()
        system_content = (
            "You are a senior site reliability engineer triaging production incidents at minute five.\n"
            "Analyze the provided alert, logs, and context, and return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            "  \"pattern\": \"<one of the valid pattern tags>\",\n"
            "  \"root_cause\": \"<1-2 sentence root cause explanation>\",\n"
            "  \"severity\": \"sev-1 | sev-2 | sev-3\",\n"
            "  \"first_action\": \"<immediate runbook action at minute five>\",\n"
            "  \"escalate\": true | false\n"
            "}\n"
            "Do not include preamble or code fences. Output raw JSON only."
        )
        msgs = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": c["user_prompt"]}
        ]
        prompt = renderer.build_generation_prompt(msgs)
        try:
            fut = sampler.sample(prompt=prompt, num_samples=1, sampling_params=params)
            res = fut.result()
            elapsed = time.time() - t0
            tokens = list(res.sequences[0].tokens)
            msg, termination = renderer.parse_response(tokens)
            raw_text = get_text_content(msg)

            cleaned = clean_json(raw_text)
            parsed = json.loads(cleaned) if cleaned else {}
            json_valid = isinstance(parsed, dict) and "pattern" in parsed

            pred_pattern = parsed.get("pattern", "")
            pred_sev = normalize_severity(parsed.get("severity", ""))
            pred_esc = bool(parsed.get("escalate", False))

            exact_pat, fuzzy_pat = match_pattern(pred_pattern, c["gold_pattern"])
            sev_match = (pred_sev == c["gold_severity"])
            esc_match = (pred_esc == c["gold_escalate"])
            false_esc = (pred_esc and not c["gold_escalate"])
            missed_esc = (not pred_esc and c["gold_escalate"])

            eval_row = {
                "id": c["id"],
                "gold_pattern": c["gold_pattern"],
                "pred_pattern": pred_pattern,
                "gold_severity": c["gold_severity"],
                "pred_severity": pred_sev,
                "gold_escalate": c["gold_escalate"],
                "pred_escalate": pred_esc,
                "exact_pattern_match": exact_pat,
                "fuzzy_pattern_match": fuzzy_pat,
                "severity_match": sev_match,
                "escalate_match": esc_match,
                "false_escalation": false_esc,
                "missed_escalation": missed_esc,
                "json_valid": json_valid,
                "latency": elapsed,
                "raw_output": raw_text[:500]
            }
        except Exception as e:
            elapsed = time.time() - t0
            eval_row = {
                "id": c["id"],
                "gold_pattern": c["gold_pattern"],
                "error": str(e),
                "json_valid": False,
                "exact_pattern_match": False,
                "fuzzy_pattern_match": False,
                "severity_match": False,
                "escalate_match": False,
                "false_escalation": False,
                "missed_escalation": False,
                "latency": elapsed
            }

        results.append(eval_row)
        icon = "✓" if eval_row.get("exact_pattern_match") else ("~" if eval_row.get("fuzzy_pattern_match") else "✗")
        print(f"[{idx+1}/{len(cases)}] {icon} {c['id']} | Gold: {c['gold_pattern']} | Pred: {eval_row.get('pred_pattern', 'ERR')} ({eval_row['latency']:.2f}s)")

    sampler.close()
    service.close()

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
    print(f"MUSE GLIMMER 30B (BASE) EVALUATION SUMMARY")
    print("="*50)
    print(f"Total Cases:                 {total}")
    print(f"JSON Validity:               {json_valid_cnt}/{total} ({json_valid_cnt/total*100:.1f}%)")
    print(f"Exact Pattern Accuracy:      {exact_pat_cnt}/{total} ({exact_pat_cnt/total*100:.1f}%)")
    print(f"Fuzzy/Semantic Pattern Acc:  {fuzzy_pat_cnt}/{total} ({fuzzy_pat_cnt/total*100:.1f}%)")
    print(f"Severity Classification Acc: {sev_cnt}/{total} ({sev_cnt/total*100:.1f}%)")
    print(f"Escalation Decision Acc:     {esc_cnt}/{total} ({esc_cnt/total*100:.1f}%)")
    print(f"False Escalation (Wolf):     {false_esc_cnt}")
    print(f"Missed Escalation (Leak):    {missed_esc_cnt}")
    print(f"Average Latency:             {avg_latency:.2f}s")
    print("="*50)

    # Save results
    os.makedirs("eval_results", exist_ok=True)
    out_jsonl = "eval_results/muse_glimmer_eval_results.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    # Save Markdown report
    jv_p, jv_l, jv_u = wilson_ci(json_valid_cnt, total)
    ep_p, ep_l, ep_u = wilson_ci(exact_pat_cnt, total)
    fp_p, fp_l, fp_u = wilson_ci(fuzzy_pat_cnt, total)
    sv_p, sv_l, sv_u = wilson_ci(sev_cnt, total)
    es_p, es_l, es_u = wilson_ci(esc_cnt, total)
    fe_p, fe_l, fe_u = wilson_ci(false_esc_cnt, total)
    me_p, me_l, me_u = wilson_ci(missed_esc_cnt, total)

    out_md = "eval_results/MUSE_GLIMMER_BASELINE_REPORT.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("# Evaluation Report: Muse Glimmer 30B (Base)\n\n")
        f.write(f"Evaluated on {total} held-out evaluation test cases (`data/eval_split_100.jsonl`) using Fireworks Serverless Sampling API (`accounts/fireworks/models/muse-glimmer-30b`).\n\n")
        f.write("## Overall Metrics (95% Wilson Confidence Intervals)\n\n")
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
        for r in results:
            match_str = "Exact" if r.get("exact_pattern_match") else ("Fuzzy" if r.get("fuzzy_pattern_match") else "Miss")
            f.write(f"| `{r['id']}` | `{r.get('gold_pattern')}` | `{r.get('pred_pattern', 'N/A')}` | {match_str} | {r.get('gold_severity')} | {r.get('pred_severity')} | {r.get('escalate_match')} |\n")

    print(f"\nSaved detailed results to {out_jsonl}")
    print(f"Saved report to {out_md}")

if __name__ == "__main__":
    main()
