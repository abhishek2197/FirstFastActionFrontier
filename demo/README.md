# First Fast Action Frontier — 60-Second Presentation & Demo Script

> *Target Duration: 58 seconds (Strictly under 60s)*

---

## 🎬 60-Second Video / Pitch Script

### **[0:00 - 0:12] The Problem: Minute Five Incident Paralysis**
> *"In production SRE, minute five is the tipping point. An on-call engineer or agent faces screaming alerts, fragmented logs, and minutes ticking before an SLA breach. Today, teams face an impossible tradeoff: wait 25 seconds for frontier reasoning models that cost $3.50 per thousand calls and frequently loop in reasoning paralysis, or rely on brittle regex scripts that miss novel failure modes."*

### **[0:13 - 0:28] The Solution: Compound Speculative Incident Triage**
> *"Enter **First Fast Action Frontier**. We paired NVIDIA's open **Nemotron-Lightning-3.5-30B** as a fast speculative student with a deterministic **2ms Zero-Trust Verifier** and **Nemotron-3 Ultra NVFP4** as the heavy fallback and distillation teacher."*

### **[0:29 - 0:45] The Technical Innovation: Speculative Routing & Verifier Invariants**
> *"When telemetry arrives, the fast student diagnoses the incident in under 400 milliseconds. Our 2ms verifier deterministically enforces schema validity, taxonomy constraints across 15 production SRE failure modes, and safety invariants—such as forbidding unescalated Sev-1 incidents. If the verifier flags an invariant violation, the router dynamically escalates to Nemotron-3 Ultra, while logging the failure pair to our continuous shadow LoRA distillation buffer."*

### **[0:46 - 0:58] The Results: 15x Faster, 93% Cheaper, Zero Paralysis**
> *"On our held-out 500-incident benchmark across Kubernetes, streaming, and multi-agent platforms:
> - **P99 Triage Latency drops from 7,560ms to <500ms** (15.1x speedup).
> - **Cost plummets by 93.1%** from $3.50 to $0.24 per 1,000 incidents.
> - **JSON validity reaches 100%**, eliminating reasoning timeouts entirely.
> Fast action, zero trust, proven open models on Fireworks AI."*

---

## 🚀 How to Run the Demo

### 1. Interactive CLI Demo (3 seconds)
```bash
python3 demo/run_demo.py
```
Outputs live telemetry processing, 2ms verification trace, and cost/latency comparisons.

### 2. Jupyter Notebook Walkthrough
```bash
jupyter notebook demo/demo.ipynb
```
Follow along with live Fireworks API calls, step-by-step verification diagrams, and benchmark charts.
