# Run Manifest: minute-five-nemotron-30b-v1

- **Run ID:** `minute-five-nemotron-30b-v1`
- **Account:** `accounts/itas97`
- **Entry Skill:** `configure`
- **Creation Time:** `2026-11-02T12:52:00-08:00`
- **Base Model:** `accounts/fireworks/models/nemotron-nano-3-30b-a3b`
- **Method:** LoRA SFT
- **Surface:** Managed SFT (`supervisedFineTuningJobs`) on B200 LoRA
- **Training Shape:** `accounts/fireworks/trainingShapes/nemotron-nano-3-30b-a3b-262k-b200-lora`
- **Dataset:** `accounts/itas97/datasets/minute-five-synthetic-triage` (75 rows, CHAT format)
- **Parameters:**
  - `epochs`: 3
  - `lora_rank`: 16
  - `learning_rate`: 0.0001
  - `max_context_length`: 4096
  - `eval_auto_carveout`: true
- **User Approval:**
  > "Approved and start the training job"
