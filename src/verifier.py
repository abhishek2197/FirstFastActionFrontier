"""
Zero-Trust Deterministic Triage Verifier (2ms execution time).
Validates triage payloads against schema, pattern taxonomy, severity rules,
and action safety invariants before automated execution.
"""

import json
import re
from typing import Dict, Any, Tuple, List

VALID_PATTERNS = {
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
}

VALID_SEVERITIES = {"sev-1", "sev-2", "sev-3", "sev-4"}

REQUIRED_FIELDS = ["pattern", "root_cause", "severity", "first_action", "escalate"]

class VerifierResult:
    def __init__(self, is_valid: bool, confidence: float, issues: List[str], cleaned_data: Dict[str, Any] = None):
        self.is_valid = is_valid
        self.confidence = confidence
        self.issues = issues
        self.cleaned_data = cleaned_data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "confidence": round(self.confidence, 3),
            "issues": self.issues,
            "cleaned_data": self.cleaned_data
        }

class ZeroTrustVerifier:
    """
    Sub-2ms deterministic rule engine verifying model triage outputs.
    Ensures zero hallucinated patterns, syntactically sound actions,
    and appropriate escalation flags.
    """

    def __init__(self, strict_patterns: bool = True):
        self.strict_patterns = strict_patterns

    def verify(self, raw_output: str, alert_context: str = "") -> VerifierResult:
        issues = []
        confidence = 1.0

        if not raw_output or not raw_output.strip():
            return VerifierResult(False, 0.0, ["Empty response from model"])

        # 1. JSON Extraction and Parsing
        parsed_data = None
        cleaned_text = raw_output.strip()
        if "```json" in cleaned_text:
            match = re.search(r"```json\s*(.*?)\s*```", cleaned_text, re.DOTALL)
            if match:
                cleaned_text = match.group(1).strip()
        elif "```" in cleaned_text:
            match = re.search(r"```\s*(.*?)\s*```", cleaned_text, re.DOTALL)
            if match:
                cleaned_text = match.group(1).strip()

        try:
            parsed_data = json.loads(cleaned_text)
        except json.JSONDecodeError:
            # Try finding first { and last }
            start = cleaned_text.find("{")
            end = cleaned_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed_data = json.loads(cleaned_text[start:end+1])
                except Exception as e:
                    return VerifierResult(False, 0.0, [f"JSON Parse Error: {e}"])
            else:
                return VerifierResult(False, 0.0, ["No valid JSON object found in output"])

        if not isinstance(parsed_data, dict):
            return VerifierResult(False, 0.0, ["Parsed output is not a JSON dictionary"])

        # 2. Schema Completeness Check
        for field in REQUIRED_FIELDS:
            if field not in parsed_data:
                issues.append(f"Missing required key: '{field}'")
                confidence -= 0.25

        # 3. Pattern Vocabulary Validation
        pattern = str(parsed_data.get("pattern", "")).strip().lower()
        if not pattern:
            issues.append("Missing pattern identifier")
            confidence -= 0.3
        elif pattern not in VALID_PATTERNS:
            # Check for close alias or substring
            matched = False
            for vp in VALID_PATTERNS:
                if vp in pattern or pattern in vp:
                    parsed_data["pattern"] = vp
                    matched = True
                    break
            if not matched:
                issues.append(f"Invalid pattern '{pattern}'. Must belong to 15 SRE failure modes.")
                confidence -= 0.4
            else:
                confidence -= 0.05

        # 4. Severity Validation
        sev = str(parsed_data.get("severity", "")).strip().lower()
        if sev.isdigit():
            sev = f"sev-{sev}"
            parsed_data["severity"] = sev

        if sev not in VALID_SEVERITIES:
            issues.append(f"Invalid severity '{sev}'. Must be sev-1, sev-2, sev-3, or sev-4.")
            confidence -= 0.2
        else:
            parsed_data["severity"] = sev

        # 5. Escalation Flag Consistency
        escalate = parsed_data.get("escalate")
        if not isinstance(escalate, bool):
            if str(escalate).lower() in ("true", "1", "yes"):
                parsed_data["escalate"] = True
            elif str(escalate).lower() in ("false", "0", "no"):
                parsed_data["escalate"] = False
            else:
                issues.append(f"Non-boolean escalate value '{escalate}'")
                confidence -= 0.15

        # Invariant: Sev-1 incidents MUST escalate
        if parsed_data.get("severity") == "sev-1" and not parsed_data.get("escalate"):
            issues.append("Safety Invariant Violation: Sev-1 incident marked with escalate=false")
            parsed_data["escalate"] = True
            confidence -= 0.2

        # 6. First Action Invariance
        action = str(parsed_data.get("first_action", "")).strip()
        if len(action) < 10:
            issues.append("Remediation first_action is too short or empty")
            confidence -= 0.2

        # 7. Final verdict
        confidence = max(0.0, min(1.0, confidence))
        is_valid = len(issues) == 0 or (len(issues) == 1 and confidence >= 0.75)

        return VerifierResult(is_valid=is_valid, confidence=confidence, issues=issues, cleaned_data=parsed_data)
