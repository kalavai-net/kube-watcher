import time
import requests
import base64


t = time.time()
model_id = "CompVis/stable-diffusion-v1-4"
#model_id = "stable-diffusion-v1-5/stable-diffusion-v1-5"
prompt = "A children's book drawing of a veterinarian using a stethoscope to listen to the heartbeat of a baby otter."
resp = requests.post(
    f"http://127.0.0.1:8000/v1/images/generations",
    json={
        "prompt": prompt,
        "model": model_id,
        "n": 2,
        "size": "512x512",
        "response_format": "b64_json"
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

