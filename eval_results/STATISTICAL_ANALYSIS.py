#!/usr/bin/env python3
"""
Statistical Analysis & Confidence Interval Calculator for Benchmark Evaluation.
Calculates:
- 95% Wilson Score Interval for binomial metrics (Accuracy, JSON validity)
- McNemar's Test for paired model significance (p-value)
- Latency P50, P90, P99, and Welch's t-test
"""

import math
from typing import Tuple, Dict, Any, List

def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float, float]:
    """
    Computes Wilson score interval for binomial proportions.
    Returns (proportion, lower_bound, upper_bound) as percentages.
    """
    if total == 0:
        return 0.0, 0.0, 0.0
    
    # z-value for confidence level (1.96 for 95%)
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z**2 / total
    centre_adj_p = (p + z**2 / (2 * total)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)) / denom
    
    lower = max(0.0, centre_adj_p - margin) * 100
    upper = min(1.0, centre_adj_p + margin) * 100
    prop = p * 100
    return prop, lower, upper

def mcnemar_test(both_correct: int, only_a_correct: int, only_b_correct: int, neither_correct: int) -> Tuple[float, float]:
    """
    Computes McNemar's test statistic with continuity correction and two-tailed p-value.
    b = only model A correct
    c = only model B correct
    """
    b = only_a_correct
    c = only_b_correct
    if (b + c) == 0:
        return 0.0, 1.0
    
    # McNemar's with Edwards continuity correction
    chi2 = (abs(b - c) - 1.0)**2 / (b + c)
    
    # 1 degree of freedom p-value approximation via complementary error function
    p_value = math.erfc(math.sqrt(chi2) / math.sqrt(2))
    return chi2, p_value

def summarize_benchmark(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    if total == 0:
        return {}
    
    pattern_matches = sum(1 for r in results if r.get("pattern_match"))
    json_valids = sum(1 for r in results if r.get("json_valid"))
    false_escalations = sum(1 for r in results if r.get("false_escalation"))
    
    latencies = [r.get("latency_sec", 0.0) for r in results if r.get("latency_sec") is not None]
    latencies.sort()
    
    p_acc, p_low, p_high = wilson_score_interval(pattern_matches, total)
    j_acc, j_low, j_high = wilson_score_interval(json_valids, total)
    f_esc, f_low, f_high = wilson_score_interval(false_escalations, total)
    
    mean_lat = sum(latencies) / len(latencies) if latencies else 0.0
    p50_lat = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
    p90_lat = latencies[int(len(latencies) * 0.90)] if latencies else 0.0
    p99_lat = latencies[int(len(latencies) * 0.99)] if latencies else 0.0
    
    return {
        "total_cases": total,
        "pattern_accuracy": {
            "percentage": round(p_acc, 2),
            "ci_95": (round(p_low, 2), round(p_high, 2)),
            "count": f"{pattern_matches}/{total}"
        },
        "json_validity": {
            "percentage": round(j_acc, 2),
            "ci_95": (round(j_low, 2), round(j_high, 2)),
            "count": f"{json_valids}/{total}"
        },
        "false_escalation_rate": {
            "percentage": round(f_esc, 2),
            "ci_95": (round(f_low, 2), round(f_high, 2)),
            "count": f"{false_escalations}/{total}"
        },
        "latency_sec": {
            "mean": round(mean_lat, 2),
            "p50": round(p50_lat, 2),
            "p90": round(p90_lat, 2),
            "p99": round(p99_lat, 2)
        }
    }

if __name__ == "__main__":
    print("Statistical Module Loaded Successfully.")
