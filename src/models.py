"""
Fireworks Model Inference Client for First Fast Action Frontier.
Supports:
- Nemotron-Lightning-3.5-30B (Fast Student / Baseline)
- Nemotron-3-Ultra-NVFP4 (High-Capacity Frontier Teacher)
- Fine-tuned custom checkpoints
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple

LIGHTNING_MODEL = os.environ.get("STUDENT_MODEL", "accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b")
ULTRA_MODEL = "accounts/fireworks/models/nemotron-3-ultra-nvfp4"

TRIAGE_SYSTEM_PROMPT = (
    "You are a senior site reliability engineer triaging a production incident at minute five. "
    "Analyze the provided alert, telemetry logs, and environment context. "
    "Diagnose the failure pattern, root cause, severity (sev-1, sev-2, sev-3, sev-4), "
    "prescribe the immediate first action, and decide whether to escalate. "
    "Return ONLY valid JSON matching this schema:\n"
    "{\n"
    '  "pattern": "<pattern_name>",\n'
    '  "root_cause": "<concise description of underlying flaw>",\n'
    '  "severity": "<sev-1 | sev-2 | sev-3 | sev-4>",\n'
    '  "first_action": "<concrete mitigation action>",\n'
    '  "escalate": <true | false>\n'
    "}"
)

class ModelClient:
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            api_key = os.environ.get("FIREWORKS_API_KEY")
            if not api_key and os.path.exists(".env"):
                with open(".env") as f:
                    for line in f:
                        if line.startswith("FIREWORKS_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        if not api_key:
            raise ValueError("FIREWORKS_API_KEY not found in environment or .env file.")
        self.api_key = api_key
        self.url = "https://api.fireworks.ai/inference/v1/chat/completions"

    def triage(
        self,
        alert: str,
        logs: str,
        context: str,
        model: str = LIGHTNING_MODEL,
        max_tokens: int = 16384,
        temperature: float = 0.1,
        timeout: int = 60
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Sends an incident to the specified model and returns (raw_content, latency_sec, usage_stats).
        """
        user_message = f"[ALERT]\n{alert}\n\n[LOGS]\n{logs}\n\n[CONTEXT]\n{context}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_k": 40
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed = time.time() - start_time
                res = json.loads(resp.read().decode("utf-8"))
                choice = res["choices"][0]
                message = choice.get("message", {})
                content = message.get("content") or ""
                reasoning = message.get("reasoning_content") or ""
                usage = res.get("usage", {})
                usage["reasoning_len"] = len(reasoning)
                return content, elapsed, usage
        except Exception as e:
            elapsed = time.time() - start_time
            return f'{{"error": "{str(e)}"}}', elapsed, {"error": str(e)}
