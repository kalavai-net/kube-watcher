# Model Quantization Tool

This tool downloads models from Hugging Face, quantizes them (FP8 8-bit or NF4 4-bit), and uploads them back to Hugging Face. It supports both GPU and CPU execution.

## Features

- **Automatic GPU/CPU detection**: Automatically detects and uses available GPUs, with fallback to CPU
- **Multiple quantization formats**: FP8 (8-bit) on GPU or CPU, NF4 (4-bit) on GPU
- **FP8 quantization**: Uses bitsandbytes for efficient 8-bit quantization (GPU) or direct weight casting (CPU)
- **NF4 quantization**: 4-bit Normal Float quantization via bitsandbytes (GPU only, ~50% smaller than FP8)
- **Low-memory mode**: Processes weight shards one at a time, so even large models can be quantized with limited RAM
- **Hugging Face integration**: Direct download and upload to/from Hugging Face Hub
- **Flexible configuration**: Command-line options for various scenarios
- **Error handling**: Comprehensive error handling and logging

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Hugging Face token (optional but recommended for uploads):
```bash
export HF_TOKEN="your_huggingface_token_here"
```

## Usage

### Basic Usage

Download, quantize, and upload a model:
```bash
python quantize_model.py --model-name "meta-llama/Llama-2-7b-hf" --output-repo "your-username/Llama-2-7b-fp8"
```

### CPU-only Mode

Force CPU usage even if GPU is available:
```bash
python quantize_model.py --model-name "meta-llama/Llama-2-7b-hf" --output-repo "your-username/Llama-2-7b-fp8" --cpu-only
```

### Local Only (Skip Upload)

Save quantized model locally without uploading:
```bash
python quantize_model.py --model-name "mistralai/Mistral-Small-3.2-24B-Instruct-2506" --output-repo "kalavai/Mistral-Small-3.2-24B-Instruct-2506-FP8" --skip-upload --local-path "./Mistral-Small-3.2-24B-Instruct-2506-FP8"
```

### Low-Memory Mode

For machines with limited RAM, process weight shards one at a time (only one shard is loaded into memory at any point):
```bash
python quantize_model.py --model-name "Qwen/Qwen3-4B" --output-repo "your-username/Qwen3-4B-fp8" --low-memory --skip-upload --local-path "./Qwen3-4B-FP8" --cpu-only
```

### 4-bit Quantization (GPU required)

Quantize to NF4 (4-bit) for maximum compression:
```bash
python quantize_model.py --model-name "Qwen/Qwen3-4B" --output-repo "your-username/Qwen3-4B-nf4" --bits 4 --skip-upload --local-path "./Qwen3-4B-NF4"
```

### Private Repository

Upload to a private repository:
```bash
python quantize_model.py --model-name "meta-llama/Llama-2-7b-hf" --output-repo "your-username/Llama-2-7b-fp8" --private
```

## Command Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `--model-name` | Name of the model to download from Hugging Face | ✅ |
| `--output-repo` | Name of the repository to upload the quantized model | ✅ |
| `--local-path` | Local path to save the quantized model (default: `./quantized_model`) | ❌ |
| `--token` | Hugging Face API token (or set `HF_TOKEN` environment variable) | ❌ |
| `--private` | Create a private repository | ❌ |
| `--cpu-only` | Force CPU usage even if GPU is available | ❌ |
| `--low-memory` | Process weight shards one at a time to minimize RAM usage (CPU only, slower) | ❌ |
| `--bits` | Quantization bit width: `8` for FP8, `4` for NF4 (default: 8). 4-bit requires GPU. | ❌ |
| `--verbose` | Enable verbose logging | ❌ |
| `--skip-upload` | Skip uploading to Hugging Face (only save locally) | ❌ |

## GPU Requirements

- **Recommended**: NVIDIA GPU with at least 8GB VRAM
- **Minimum**: NVIDIA GPU with 4GB VRAM (may be slow)
- **CPU fallback**: Supported but quantization quality may be reduced

## Supported Models

The script works with most transformer-based models available on Hugging Face, including:
- LLaMA family (meta-llama/*)
- Mistral models (mistralai/*)
- Falcon models (tiiuae/*)
- BLOOM models (bigscience/*)
- And many more...

## Example Workflows

### Quantize LLaMA-2-7B for GPU
```bash
python quantize_model.py \
  --model-name "meta-llama/Llama-2-7b-hf" \
  --output-repo "my-username/Llama-2-7b-fp8" \
  --verbose
```

### Quantize Mistral-7B on CPU
```bash
python quantize_model.py \
  --model-name "mistralai/Mistral-7B-v0.1" \
  --output-repo "my-username/Mistral-7B-fp8" \
  --cpu-only \
  --local-path "./mistral_fp8"
```

### Batch quantization (example script)
```bash
#!/bin/bash
models=(
  "meta-llama/Llama-2-7b-hf"
  "mistralai/Mistral-7B-v0.1"
  "tiiuae/falcon-7b"
)

for model in "${models[@]}"; do
  repo_name="my-username/$(basename $model)-fp8"
  python quantize_model.py --model-name "$model" --output-repo "$repo_name" --skip-upload
done
```

## Testing Quantized Models

Use `test_model.py` to quickly verify a quantized model works:

```bash
python test_model.py --model-path "./Qwen3-4B-FP8"
```

Custom prompt and token count:
```bash
python test_model.py --model-path "./Qwen3-4B-FP8" --prompt "Explain quantum computing in simple terms:" --max-tokens 100
```

It will print the generated text along with speed and dtype info.

## Troubleshooting

### Common Issues

1. **Out of Memory**: Use `--low-memory` to process shards one at a time, drastically reducing peak RAM usage
2. **Permission Denied**: Check your Hugging Face token and repository permissions
3. **Model Not Found**: Verify the model name exists on Hugging Face
4. **bitsandbytes Error**: Ensure you have a compatible NVIDIA GPU and CUDA installation

### Logs

Use `--verbose` flag to see detailed logging information:
```bash
python quantize_model.py --model-name "meta-llama/Llama-2-7b-hf" --output-repo "test-repo" --verbose
```

## Performance Notes

- **GPU quantization**: Typically 2-5x faster than CPU
- **FP8 memory usage**: Reduces model size by ~50% compared to FP16
- **NF4 memory usage**: Reduces model size by ~75% compared to FP16
- **Quality**: FP8 maintains near-lossless quality; NF4 has slightly more degradation but is excellent for inference
- **4-bit limitation**: NF4 requires GPU (bitsandbytes CUDA); not available on CPU or in low-memory mode

## License

This tool is provided as-is. Please ensure you have the right to quantize and redistribute models according to their original licenses.
