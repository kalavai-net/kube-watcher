# Image Generation API Documentation

## Overview

This API provides OpenAI-compatible image generation capabilities using various diffusion models. The service is built on Ray Serve for scalable deployment and supports multiple model types and schedulers for optimized performance.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required. This may change in production deployments.

## Endpoints

### POST /v1/images/generations

Generates one or more images from a text prompt using diffusion models.

**Request Format:**
```http
POST /v1/images/generations
Content-Type: application/json
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | A text description of the desired image. Be descriptive for better results. |
| `model` | string | No | "stable-diffusion-v1-5" | The model to use for image generation. See [Supported Models](#supported-models). |
| `n` | integer | No | 1 | The number of images to generate. Range: 1-10. |
| `size` | string | No | "512x512" | The size of generated images. Format: "WIDTHxHEIGHT". Only square sizes supported: 256x256, 512x512, 1024x1024. |
| `quality` | string | No | "standard" | The quality of the image. Currently only "standard" is supported. |
| `response_format` | string | No | "b64_json" | Format for returned images. Options: "b64_json" (base64 encoded), "url" (not implemented yet). |
| `style` | string | No | null | The style of generated images. Optional, model-dependent. |
| `user` | string | No | null | A unique identifier representing your end-user. Useful for rate limiting and monitoring. |
| `extra` | object | No | null | Extra parameters for diffusers pipeline (e.g., num_inference_steps, guidance_scale). |
| `scheduler` | string | No | "euler_ancestral" | Scheduler algorithm for generation. See [Available Schedulers](#available-schedulers). |
| `compile` | boolean | No | true | Whether to compile the pipeline for faster inference (CUDA only). |
| `batch_size` | integer | No | 1 | Batch size for parallel generation. Range: 1-4. |

#### Supported Models

| Model ID | Pipeline Type | Description |
|----------|---------------|-------------|
| `stable-diffusion-v1-5/stable-diffusion-v1-5` | AutoPipelineForText2Image | Standard Stable Diffusion v1.5 |
| `CompVis/stable-diffusion-v1-4` | AutoPipelineForText2Image | Stable Diffusion v1.4 |
| `black-forest-labs/FLUX.1-dev` | FluxPipeline | FLUX.1 development model |
| `black-forest-labs/FLUX.2-klein-4B` | Flux2KleinPipeline | FLUX.2 Klein 4B model |

#### Available Schedulers

| Scheduler | Description | Use Case |
|-----------|-------------|----------|
| `euler_ancestral` | Euler Ancestral Discrete Scheduler | Good balance of quality and speed |
| `dpmpp_2m` | DPM-Solver++ 2M | Higher quality, slightly slower |
| `unipc` | UniPC Multistep Scheduler | Fast convergence, good quality |
| `lcm` | LCM Scheduler | Ultra-fast generation (4 steps), lower quality |

#### Response Format

```json
{
  "created": 1640995200,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgAA...",
      "revised_prompt": null,
      "url": null
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `created` | integer | Unix timestamp of generation |
| `data` | array | Array of generated image data |
| `data[].b64_json` | string | Base64-encoded PNG image |
| `data[].revised_prompt` | string | Potentially revised prompt (null for now) |
| `data[].url` | string | Image URL (null, not implemented) |

## Example Requests

### Basic Image Generation

```bash
curl -X POST "http://localhost:8000/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "n": 1,
    "size": "512x512"
  }'
```

### Multiple Images with Custom Settings

```bash
curl -X POST "http://localhost:8000/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cute robot reading a book in a cozy library, digital art style",
    "model": "stable-diffusion-v1-5/stable-diffusion-v1-5",
    "n": 3,
    "size": "1024x1024",
    "scheduler": "dpmpp_2m",
    "batch_size": 2,
    "extra": {
      "num_inference_steps": 30,
      "guidance_scale": 7.5
    }
  }'
```

### Fast Generation with LCM Scheduler

```bash
curl -X POST "http://localhost:8000/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A futuristic cityscape at night",
    "model": "CompVis/stable-diffusion-v1-4",
    "n": 1,
    "size": "512x512",
    "scheduler": "lcm",
    "extra": {
      "num_inference_steps": 4,
      "guidance_scale": 1.0
    }
  }'
```

### FLUX Model Generation

```bash
curl -X POST "http://localhost:8000/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A photorealistic portrait of a scientist in a laboratory",
    "model": "black-forest-labs/FLUX.1-dev",
    "n": 2,
    "size": "1024x1024",
    "compile": true,
    "extra": {
      "num_inference_steps": 25,
      "guidance_scale": 3.5
    }
  }'
```

### Python Example

```python
import requests
import base64
from PIL import Image
import io

# API endpoint
url = "http://localhost:8000/v1/images/generations"

# Request payload
payload = {
    "prompt": "A majestic dragon flying over a medieval castle",
    "model": "stable-diffusion-v1-5/stable-diffusion-v1-5",
    "n": 2,
    "size": "512x512",
    "scheduler": "euler_ancestral",
    "extra": {
        "num_inference_steps": 20,
        "guidance_scale": 7.0
    }
}

# Make request
response = requests.post(url, json=payload)
data = response.json()

# Process images
for i, image_data in enumerate(data["data"]):
    # Decode base64 image
    image_bytes = base64.b64decode(image_data["b64_json"])
    image = Image.open(io.BytesIO(image_bytes))
    
    # Save image
    image.save(f"generated_image_{i+1}.png")
    print(f"Saved image {i+1}")
```

## Additional Endpoints

### GET /v1/models

List all available models.

```bash
curl -X GET "http://localhost:8000/v1/models"
```

### GET /health

Health check endpoint.

```bash
curl -X GET "http://localhost:8000/health"
```

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `500`: Internal Server Error
- `501`: Not Implemented (feature not available)

Error response format:
```json
{
  "error": {
    "message": "Error description",
    "type": "invalid_request_error"
  }
}
```

## Performance Tips

1. **Use batch processing**: Set `batch_size` > 1 when generating multiple images
2. **Choose appropriate scheduler**: Use `lcm` for speed, `dpmpp_2m` for quality
3. **Enable compilation**: Keep `compile: true` for CUDA devices
4. **Optimize size**: Use smaller sizes (512x512) for faster generation
5. **Model selection**: FLUX models may be slower but produce higher quality results

## Limitations

- Only square image sizes are supported (256x256, 512x512, 1024x1024)
- URL response format is not yet implemented
- Image editing and variation endpoints are not implemented
- Model switching may cause delays due to loading times
- Compilation is only available on CUDA devices
