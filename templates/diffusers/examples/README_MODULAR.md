# Flux 2 Klein Modular Pipeline with Remote API Components

This example demonstrates how to create a modular diffusion pipeline using the new [Modular Diffusers](https://huggingface.co/blog/modular-diffusers) framework, where large components (transformer and text encoder) are offloaded to remote API servers while the VAE runs locally.

## 🎯 Benefits

1. **Reuse components across multiple pipelines** - Share expensive models between different workflows
2. **Scale beyond single machine limits** - Load larger models by distributing them across multiple servers
3. **Independent scaling** - Scale text encoding and denoising separately based on your workload
4. **Flexible deployment** - Mix local and remote components as needed

## 📁 Files

- **`modular.py`** - Main modular pipeline with custom remote blocks
- **`api_text_encoder_server.py`** - REST API server for text encoding
- **`api_transformer_server.py`** - REST API server for transformer denoising

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Modular Pipeline Client                 │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────┐      ┌──────────────────┐         │
│  │ Remote Text      │──────│ Remote           │         │
│  │ Encoder Block    │ HTTP │ Transformer      │         │
│  │ (API Call)       │      │ Block (API Call) │         │
│  └──────────────────┘      └──────────────────┘         │
│           │                         │                    │
│           │                         │                    │
│           ▼                         ▼                    │
│  ┌──────────────────────────────────────────┐           │
│  │         Local VAE Decode Block           │           │
│  │         (Default Component)              │           │
│  └──────────────────────────────────────────┘           │
│                      │                                   │
│                      ▼                                   │
│                  Final Image                             │
└─────────────────────────────────────────────────────────┘
                       │
                       │ HTTP Requests
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────┐            ┌────────────────┐
│ Text Encoder  │            │  Transformer   │
│ API Server    │            │  API Server    │
│ (Port 8001)   │            │  (Port 8002)   │
│               │            │                │
│ - CLIP        │            │ - Flux         │
│ - T5          │            │   Transformer  │
│               │            │ - Scheduler    │
└───────────────┘            └────────────────┘
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install diffusers transformers torch accelerate requests fastapi uvicorn numpy
```

### 2. Start the API Servers

**Terminal 1 - Text Encoder Server:**
```bash
cd templates/diffusers/examples
PORT=8001 DEVICE=cuda MODEL_ID=black-forest-labs/FLUX.2-klein-4B python api_text_encoder_server.py
```

**Terminal 2 - Transformer Server:**
```bash
cd templates/diffusers/examples
PORT=8002 DEVICE=cuda MODEL_ID=black-forest-labs/FLUX.2-klein-4B python api_transformer_server.py
```

### 3. Run the Modular Pipeline

**Terminal 3 - Client:**
```bash
cd templates/diffusers/examples
python modular.py
```

## 📝 Usage Examples

### Basic Usage

```python
from modular import create_flux2_klein_modular_pipeline

# Create pipeline with remote components
pipeline = create_flux2_klein_modular_pipeline(
    text_encoder_api="http://localhost:8001",
    transformer_api="http://localhost:8002",
    model_id="black-forest-labs/FLUX.2-klein-4B"
)

# Generate image
image = pipeline(
    prompt="a serene landscape at sunset with mountains and a lake",
    num_inference_steps=4,
    height=1024,
    width=1024,
).images[0]

image.save("output.png")
```

### With API Authentication

```python
pipeline = create_flux2_klein_modular_pipeline(
    text_encoder_api="https://my-text-encoder.example.com",
    transformer_api="https://my-transformer.example.com",
    api_key="your-api-key-here",
    model_id="black-forest-labs/FLUX.2-klein-4B"
)
```

### Inspecting Pipeline Blocks

```python
# View all blocks in the pipeline
print(pipeline.blocks)

# Access individual blocks
text_encoder_block = pipeline.blocks.sub_blocks["text_encoder"]
transformer_block = pipeline.blocks.sub_blocks["denoise"]
vae_block = pipeline.blocks.sub_blocks["decode"]

# View block documentation
print(text_encoder_block.doc)
```

### Using Different Models

```python
# Use FLUX.2 Klein 9B instead
pipeline = create_flux2_klein_modular_pipeline(
    text_encoder_api="http://localhost:8001",
    transformer_api="http://localhost:8002",
    model_id="black-forest-labs/FLUX.2-klein-9B"
)
```

## 🔧 Custom Block Implementation

### RemoteTextEncoderBlock

This block replaces the local text encoder with an API call:

- **Inputs**: `prompt`, `prompt_2` (optional), `max_sequence_length`
- **Outputs**: `prompt_embeds`, `pooled_prompt_embeds`
- **API Endpoint**: `POST /encode`

### RemoteTransformerBlock

This block replaces the local transformer with an API call:

- **Inputs**: `prompt_embeds`, `pooled_prompt_embeds`, `num_inference_steps`, `guidance_scale`, `height`, `width`
- **Outputs**: `latents`
- **API Endpoint**: `POST /denoise`
- **Expected Components**: `scheduler` (loaded locally for timestep management)

### Default VAE Block

The VAE decoder remains local and uses the default Flux 2 Klein implementation.

## 🌐 API Endpoints

### Text Encoder API

**POST /encode**
```json
{
  "prompt": "a serene landscape",
  "prompt_2": "optional secondary prompt",
  "max_sequence_length": 512
}
```

Response:
```json
{
  "prompt_embeds": "base64_encoded_tensor",
  "prompt_embeds_shape": [1, 512, 4096],
  "pooled_prompt_embeds": "base64_encoded_tensor",
  "pooled_prompt_embeds_shape": [1, 768]
}
```

**GET /health**
```json
{
  "status": "healthy",
  "device": "cuda",
  "model_id": "black-forest-labs/FLUX.2-klein-4B"
}
```

### Transformer API

**POST /denoise**
```json
{
  "prompt_embeds": "base64_encoded_tensor",
  "prompt_embeds_shape": [1, 512, 4096],
  "pooled_prompt_embeds": "base64_encoded_tensor",
  "pooled_prompt_embeds_shape": [1, 768],
  "num_inference_steps": 4,
  "guidance_scale": 0.0,
  "height": 1024,
  "width": 1024
}
```

Response:
```json
{
  "latents": "base64_encoded_tensor",
  "latents_shape": [1, 16, 128, 128]
}
```

**GET /health**
```json
{
  "status": "healthy",
  "device": "cuda",
  "model_id": "black-forest-labs/FLUX.2-klein-4B"
}
```

## 🐳 Docker Deployment

You can containerize each API server separately for easier deployment:

**Dockerfile.text-encoder:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY api_text_encoder_server.py .
RUN pip install diffusers transformers torch fastapi uvicorn

ENV PORT=8001
ENV DEVICE=cuda

CMD ["python", "api_text_encoder_server.py"]
```

**Dockerfile.transformer:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY api_transformer_server.py .
RUN pip install diffusers transformers torch fastapi uvicorn

ENV PORT=8002
ENV DEVICE=cuda

CMD ["python", "api_transformer_server.py"]
```

Build and run:
```bash
docker build -f Dockerfile.text-encoder -t flux-text-encoder .
docker build -f Dockerfile.transformer -t flux-transformer .

docker run -p 8001:8001 --gpus all flux-text-encoder
docker run -p 8002:8002 --gpus all flux-transformer
```

## ⚙️ Configuration

### Environment Variables

**Text Encoder Server:**
- `PORT` - Server port (default: 8001)
- `DEVICE` - Device to use: cuda/cpu (default: cuda if available)
- `MODEL_ID` - HuggingFace model ID (default: black-forest-labs/FLUX.2-klein-4B)

**Transformer Server:**
- `PORT` - Server port (default: 8002)
- `DEVICE` - Device to use: cuda/cpu (default: cuda if available)
- `MODEL_ID` - HuggingFace model ID (default: black-forest-labs/FLUX.2-klein-4B)

## 🔍 Troubleshooting

### Connection Errors

If you get connection errors, ensure:
1. API servers are running and accessible
2. Firewall allows connections on ports 8001 and 8002
3. URLs in the client match the server addresses

### Memory Issues

If you run out of memory:
1. Use quantization on the API servers
2. Reduce batch size
3. Use smaller models (FLUX.2-klein-4B instead of 9B)
4. Enable VAE tiling

### Slow Performance

To improve performance:
1. Use GPU for API servers (`DEVICE=cuda`)
2. Reduce `num_inference_steps`
3. Use lower resolution (512x512 instead of 1024x1024)
4. Enable model compilation with `torch.compile()`

## 📚 Additional Resources

- [Modular Diffusers Blog Post](https://huggingface.co/blog/modular-diffusers)
- [Modular Diffusers Documentation](https://huggingface.co/docs/diffusers/en/modular_diffusers/overview)
- [FLUX.2 Model Card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)
- [Diffusers Library](https://github.com/huggingface/diffusers)

## 📄 License

This example follows the same license as the diffusers library and the FLUX.2 models.
