import time
import requests
import base64


t = time.time()
model_id = "black-forest-labs/FLUX.2-klein-4B"
prompt = "a realistic picture of a sunset with a dancing potato."
resp = requests.post(
    f"http://kalavai-api.public.kalavai.net:31311/v1/images/generations",
    json={
        "prompt": prompt,
        "model": model_id,
        "n": 1,
        "size": "512x512", # only 256x256, 512x512, 1024x1024 are supported
        "response_format": "b64_json",
        "extra": {"num_inference_steps": 10} # supported parameters https://huggingface.co/docs/diffusers/api/pipelines/flux#diffusers.FluxPipeline
    },
)
print(f"Inference time: {time.time()-t:.2f}s")

# Debug: Print the response structure
print("Response status:", resp.status_code)

for i in range(len(resp.json()["data"])):
    image_data = resp.json()["data"][i].get("b64_json")
    if image_data is None:
        print(f"Warning: No b64_json data found for image {i}")
        print(f"Available keys: {list(resp.json()['data'][i].keys())}")
        continue
    
    with open(f"output_{i}.png", 'wb') as f:
        f.write(base64.b64decode(image_data))

