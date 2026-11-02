# Minute Five — On-Call Incident Triage, Fine-Tuned

Teaching an open model to triage production incidents like a senior on-call:
given an alert and a log excerpt at minute five — cause unknown — return the
pattern, the root cause, the severity, the first action, and whether to escalate.

Built at the Fireworks Deploy Buildathon (Nov 2, 2026).

## What it does

**Input:** a pipeline incident — alert text, log excerpt, and context
(recent deploys, affected tables).

**Output:** structured triage, every time, in a fixed schema:

    {
      "pattern": "poison_pill",
      "root_cause": "poison record",
      "severity": "sev-3",
      "first_action": "skip-and-quarantine the record, alert on it, move on",
      "escalate": false
    }

## Approach: distillation via SFT

1. **Spec cards, not scraped data.** Each incident family is defined by a
   spec card — signature signals, gold triage label, variation axes, and one
   embedded red herring. Incidents are generated *from* the label, so the
   gold answer is correct by construction.
2. **Teacher-generated curriculum.** A frontier model (Muse Spark) generates
   realistic incidents from the spec cards. Every example is verified:
   programmatic checks (schema, label set, dedupe), a model cross-check
   (solver sees the incident only; disagreement = drop or fix), and human
   spot-checks.
3. **Student.** LoRA SFT of NVIDIA Nemotron Nano 3 30B A3B on Fireworks,
   trained on ~500 synthetic incidents across six pattern families:
   poison pill, schema drift, credential expiry, bad deploy, upstream
   delay, and silent corruption — with deliberate near-miss pairs
   (same symptom, different cause) and hard cases (self-healing noise →
   don't act; novel + growing → escalate despite uncertainty).

## Evaluation

Two held-out test sets, both locked before training:

- **Synthetic slice** — stratified across all six families.
- **Real slice** — 10–15 incidents adapted from public postmortems
  (danluu/post-mortems archive; Cloudflare / GitHub / AWS write-ups),
  symptoms and timeline only up to detection, published root cause as the
  gold label. Reported separately — this is the anti-circularity check.

**Metrics:** pattern accuracy, root-cause match, JSON validity,
false-escalation rate, plus latency and cost per case.

## Results (fill in after the eval run)

| Model | Pattern acc. (synthetic) | Pattern acc. (real) | JSON valid | False-escalation | Cost / case |
|---|---|---|---|---|---|
| Muse Spark (baseline) | TBD | TBD | TBD | TBD | TBD |
| Nemotron Nano 3 30B A3B (base) | TBD | TBD | TBD | TBD | TBD |
| Nemotron Nano 3 30B A3B (fine-tuned) | TBD | TBD | TBD | TBD | TBD |

## Stack

- Fireworks AI — training (LoRA SFT) and inference
- Student: NVIDIA Nemotron Nano 3 30B A3B
- Teacher / baseline: Muse Spark
- Data: synthetic incidents from spec cards + public postmortems for eval
