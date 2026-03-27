import time
import requests
import base64


t = time.time()

model_id = "black-forest-labs/FLUX.2-klein-9B"
prompt = "a cartoon of a cat."
resp = requests.post(
    #f"http://kalavai-api.public.kalavai.net:32328/v1/images/generations",
    f"http://kalavai-api.public.kalavai.net:31923/v1/images/generations",
    json={
        "prompt": prompt,
        "model": model_id,
        "n": 1,
        "batch_size": 1,
        "size": "1024x1024", # only 256x256, 512x512, 1024x1024 are supported
        "response_format": "b64_json",
        "extra": { # supported parameters https://huggingface.co/docs/diffusers/api/pipelines/flux#diffusers.FluxPipeline
            "num_inference_steps": 4,
            #"guidance_scale": 0.0,
            "max_sequence_length": 50,
            #"output_type": "np"
        }
    },
)
print(f"Inference time: {time.time()-t:.2f}s")

# Debug: Print the response structure
print("Response status:", resp.status_code)

if resp.status_code != 200:
    print("Error response received")
    print("Response content:", resp.text)
    exit(1)

for i in range(len(resp.json()["data"])):
    image_data = resp.json()["data"][i].get("b64_json")
    if image_data is None:
        print(f"Warning: No b64_json data found for image {i}")
        print(f"Available keys: {list(resp.json()['data'][i].keys())}")
        continue
    
    with open(f"output_{i}.png", 'wb') as f:
        f.write(base64.b64decode(image_data))

