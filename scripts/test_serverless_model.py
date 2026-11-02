import os
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(usecwd=True))

from fireworks.training.sdk import FiretitanServiceClient

def test_model(model_name: str):
    print(f"Testing model: {model_name} on serverless training...")
    service = FiretitanServiceClient(
        api_key=os.environ["FIREWORKS_API_KEY"],
        base_url="https://api.fireworks.ai/training/v1/serverless"
    )
    try:
        tc = service.create_lora_training_client(base_model=model_name, rank=8)
        print(f"Successfully created LoRA training client for {model_name}!")
        service.close()
        return True
    except Exception as e:
        print(f"Error testing {model_name}: {e}")
        try:
            service.close()
        except Exception:
            pass
        return False

if __name__ == "__main__":
    for m in [
        "accounts/fireworks/models/nemotron-lightning-3p5-30b-a3b",
        "accounts/fireworks/models/nemotron-nano-3-30b-a3b",
        "accounts/fireworks/models/kimi-k3",
        "accounts/fireworks/models/muse-glimmer-30b"
    ]:
        success = test_model(m)
        if success:
            print(f"--> Found supported model: {m}")
            break
