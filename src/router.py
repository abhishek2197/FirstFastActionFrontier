"""
Compound Speculative Incident Triage Router.
Implements:
1. Fast Speculative Student (Nemotron Lightning 3.5 30B)
2. Zero-Trust Deterministic Verifier (2ms latency)
3. Dynamic Teacher Escalation (Nemotron 3 Ultra NVFP4)
4. Shadow Distillation Logging for Continuous LoRA Fine-Tuning
"""

import os
import json
import time
from typing import Dict, Any, Optional

from src.models import ModelClient, LIGHTNING_MODEL, ULTRA_MODEL
from src.verifier import ZeroTrustVerifier, VerifierResult

class SpeculativeTriageRouter:
    def __init__(
        self,
        api_key: Optional[str] = None,
        confidence_threshold: float = 0.80,
        shadow_buffer_path: str = "data/shadow_distillation_buffer.jsonl"
    ):
        self.client = ModelClient(api_key=api_key)
        self.verifier = ZeroTrustVerifier()
        self.confidence_threshold = confidence_threshold
        self.shadow_buffer_path = shadow_buffer_path

    def triage_incident(
        self,
        alert: str,
        logs: str,
        context: str,
        force_teacher: bool = False
    ) -> Dict[str, Any]:
        """
        Executes speculative triage:
        - If force_teacher is False, calls fast student.
        - Verifies output in <2ms with deterministic rules.
        - If valid & confident -> routes immediately.
        - If invalid/suspicious -> escalates to Nemotron-3 Ultra and logs distillation pair.
        """
        start_time = time.time()
        combined_context = f"[ALERT]\n{alert}\n\n[LOGS]\n{logs}\n\n[CONTEXT]\n{context}"

        if force_teacher:
            teacher_output, teacher_lat, teacher_usage = self.client.triage(
                alert, logs, context, model=ULTRA_MODEL
            )
            v_res = self.verifier.verify(teacher_output)
            total_elapsed = time.time() - start_time
            return {
                "route_taken": "direct_teacher",
                "triage": v_res.cleaned_data if v_res.is_valid else teacher_output,
                "verifier_result": v_res.to_dict(),
                "latency_sec": round(total_elapsed, 3),
                "cost_estimate_usd": 0.0035, # Ultra estimate
                "student_output": None,
                "escalated": True
            }

        # Step 1: Speculative Student Fast Path
        student_output, student_lat, student_usage = self.client.triage(
            alert, logs, context, model=LIGHTNING_MODEL, max_tokens=16384, timeout=45
        )

        # Step 2: 2ms Zero-Trust Deterministic Verification
        v_start = time.time()
        v_res = self.verifier.verify(student_output, combined_context)
        verifier_time_ms = round((time.time() - v_start) * 1000, 2)

        # Step 3: Fast-Path Acceptance Criteria
        if v_res.is_valid and v_res.confidence >= self.confidence_threshold:
            total_elapsed = time.time() - start_time
            return {
                "route_taken": "fast_speculative_accepted",
                "triage": v_res.cleaned_data,
                "verifier_result": v_res.to_dict(),
                "verifier_time_ms": verifier_time_ms,
                "latency_sec": round(total_elapsed, 3),
                "cost_estimate_usd": 0.0002, # Lightning 30B estimate (15x cheaper)
                "escalated": False
            }

        # Step 4: Verification Failure -> Dynamic Escalation to Heavy Teacher
        teacher_output, teacher_lat, teacher_usage = self.client.triage(
            alert, logs, context, model=ULTRA_MODEL, max_tokens=16384, timeout=45
        )
        teacher_vres = self.verifier.verify(teacher_output, combined_context)
        total_elapsed = time.time() - start_time

        # Step 5: Log to Shadow Distillation Buffer
        self._log_shadow_pair(
            alert=alert,
            logs=logs,
            context=context,
            student_output=student_output,
            teacher_output=teacher_output,
            issues=v_res.issues,
            gold_triage=teacher_vres.cleaned_data
        )

        return {
            "route_taken": "escalated_to_teacher",
            "triage": teacher_vres.cleaned_data if teacher_vres.is_valid else teacher_output,
            "verifier_result": teacher_vres.to_dict(),
            "student_failure_issues": v_res.issues,
            "student_latency_sec": round(student_lat, 3),
            "latency_sec": round(total_elapsed, 3),
            "total_latency_sec": round(total_elapsed, 3),
            "cost_estimate_usd": 0.0037, # Student + Teacher
            "escalated": True
        }

    def _log_shadow_pair(self, alert: str, logs: str, context: str, student_output: str, teacher_output: str, issues: list, gold_triage: dict):
        if not gold_triage:
            return
        os.makedirs(os.path.dirname(self.shadow_buffer_path), exist_ok=True)
        record = {
            "timestamp": time.time(),
            "alert": alert,
            "logs": logs,
            "context": context,
            "student_output": student_output,
            "verifier_issues": issues,
            "teacher_gold_triage": gold_triage,
            "training_sample": {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a senior site reliability engineer triaging production incidents at minute five. Return only structured JSON with keys: pattern, root_cause, severity, first_action, escalate."
                    },
                    {
                        "role": "user",
                        "content": f"[ALERT]\n{alert}\n\n[LOGS]\n{logs}\n\n[CONTEXT]\n{context}"
                    },
                    {
                        "role": "assistant",
                        "content": json.dumps(gold_triage, indent=2)
                    }
                ]
            }
        }
        with open(self.shadow_buffer_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
