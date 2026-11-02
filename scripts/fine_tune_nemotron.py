#!/usr/bin/env python3
"""
Upload dataset and launch Fireworks Managed SFT Job for Nemotron Nano 3 30B A3B.
"""

import os
import sys
import time
import json
from fireworks import Fireworks, file_from_path

def load_api_key():
    key = os.environ.get("FIREWORKS_API_KEY")
    if key:
        return key.strip().strip('"')
    if os.path.exists(".env"):
        for line in open(".env"):
            if line.startswith("FIREWORKS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    raise ValueError("FIREWORKS_API_KEY not found in env or .env file")

def main():
    api_key = load_api_key()
    temp_client = Fireworks(api_key=api_key)

    # 1. Resolve Account
    account_obj = next(iter(temp_client.accounts.list(page_size=1)), None)
    if not account_obj:
        print("Error: Could not resolve account.")
        sys.exit(1)
    account = account_obj.name.split("/")[-1]
    print(f"[Preflight] Account: accounts/{account}")

    client = Fireworks(api_key=api_key, account_id=account)

    # 2. Upload / Verify Dataset
    dataset_id = "minute-five-synthetic-triage"
    dataset_name = f"accounts/{account}/datasets/{dataset_id}"
    dataset_file = "data/train_sft.jsonl"

    if not os.path.exists(dataset_file):
        print(f"Error: {dataset_file} not found.")
        sys.exit(1)

    print(f"\n[Step 1/3] Checking dataset: {dataset_name}...")
    try:
        ds = client.datasets.get(dataset_id)
        print(f"Dataset already exists with state: {ds.state}")
    except Exception:
        print(f"Uploading {dataset_file} as {dataset_id}...")
        ds = client.datasets.upload(
            dataset_id=dataset_id,
            file=file_from_path(dataset_file)
        )
        print(f"Upload initiated. Initial state: {getattr(ds, 'state', 'PENDING')}")

    # Wait for dataset READY state
    for _ in range(30):
        ds = client.datasets.get(dataset_id)
        if ds.state == "READY":
            print(f"Dataset is READY! Example count: {ds.example_count}")
            break
        print(f"Waiting for dataset processing (state: {ds.state})...")
        time.sleep(3)
    else:
        if ds.state != "READY":
            print(f"Warning: Dataset state is {ds.state}; proceeding with launch.")

    # 3. Create SFT Job
    job_id = "minute-five-nemotron-30b-v1"
    output_model_id = f"accounts/{account}/models/{job_id}"
    base_model = "accounts/fireworks/models/nemotron-nano-3-30b-a3b"

    print(f"\n[Step 2/3] Checking / Launching SFT Job: {job_id}...")
    try:
        existing = client.supervised_fine_tuning_jobs.get(job_id)
        print(f"Job {job_id} already exists with state: {existing.state}")
        job = existing
    except Exception:
        print(f"Creating Managed SFT job...")
        job = client.supervised_fine_tuning_jobs.create(
            supervised_fine_tuning_job_id=job_id,
            dataset=dataset_name,
            base_model=base_model,
            output_model=output_model_id,
            display_name="Minute Five Nemotron 30B SFT",
            epochs=3,
            lora_rank=16,
            learning_rate=0.0001,
            max_context_length=4096,
            eval_auto_carveout=True
        )
        print(f"Job created successfully! Name: {job.name}, State: {job.state}")

    # 4. Monitor Progress
    print(f"\n[Step 3/3] Monitoring Training Job: {job_id}")
    print("=" * 60)

    last_state = None
    last_pct = -1
    no_progress_start = time.time()

    for poll_idx in range(60): # Monitor for up to 10 minutes initially
        try:
            curr = client.supervised_fine_tuning_jobs.get(job_id)
            state = curr.state
            progress = getattr(curr, "job_progress", None)
            pct = getattr(progress, "percent", 0.0) if progress else 0.0
            epoch = getattr(progress, "epoch", 0.0) if progress else 0.0

            if state != last_state or pct != last_pct:
                print(f"[{time.strftime('%H:%M:%S')}] State: {state} | Progress: {pct:.1f}% | Epoch: {epoch:.2f}")
                last_state = state
                last_pct = pct
                no_progress_start = time.time()
            else:
                if time.time() - no_progress_start > 900: # 15 min stall
                    print("Warning: No progress detected for 15 minutes.")
                    break

            if state in ["JOB_STATE_COMPLETED", "COMPLETED", "SUCCESS"]:
                print(f"\n🎉 TRAINING COMPLETED SUCCESSFULLY!")
                print(f"Trained LoRA Model: {output_model_id}")
                break
            elif state in ["JOB_STATE_FAILED", "FAILED", "ERROR"]:
                print(f"\n❌ Training failed. Status message: {getattr(curr, 'status', 'Unknown error')}")
                break

            time.sleep(10)
        except Exception as e:
            print(f"Polling warning: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
