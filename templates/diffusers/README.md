# Diffusers API

Run with 
```bash
serve run ray_deploy:entrypoint --address <ray head address>
```
Inference example:

```bash
python ray_inference.py
```

Or in cURL:

```bash
curl -X POST "http://127.0.0.1:8000/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "your_prompt_here",
    "model": "your_model_id_here",
    "n": 1,
    "size": "512x512",
    "response_format": "b64_json"
  }'
```

Key environment variables:
- `HF_TOKEN`: huggingface token for gated models
- `NUM_GPUS`: number of gpus to use in the deployment
- `MIN_REPLICAS`: auto scaling replicas (min)
- `MAX_REPLICAS`: auto scaling replicas (max)