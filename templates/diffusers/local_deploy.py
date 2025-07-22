import time

import torch
from diffusers import StableDiffusionPipeline

model_id = "CompVis/stable-diffusion-v1-4"
device = "cuda"

t = time.time()
pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
pipe = pipe.to(device)
print(f"Load time", f"{time.time()-t:.2f}s")

t = time.time()
prompt = "a photo of an astronaut riding a horse on mars"
image = pipe(prompt).images[0]  
print(f"Inference time", f"{time.time()-t:.2f}s")

image.save("astronaut_rides_horse.png")