#!/usr/bin/env python3
"""
Hugging Face Model Quantization Script

This script downloads a model from Hugging Face, quantizes it (FP8 8-bit or NF4 4-bit),
and uploads it back to Hugging Face. Supports both GPU and CPU execution.
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import json
import shutil
import glob

import torch
from safetensors.torch import load_file as safetensors_load, save_file as safetensors_save
from huggingface_hub import HfApi, create_repo, snapshot_download
from transformers import AutoModelForCausalLM, AutoModel, AutoTokenizer, BitsAndBytesConfig


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def check_gpu_availability() -> bool:
    """Check if GPU is available and has sufficient memory."""
    if not torch.cuda.is_available():
        logging.info("No GPU available. Will use CPU for quantization.")
        return False
    
    gpu_count = torch.cuda.device_count()
    total_memory = sum(torch.cuda.get_device_properties(i).total_memory for i in range(gpu_count))
    
    logging.info(f"Found {gpu_count} GPU(s) with {total_memory / 1024**3:.1f}GB total memory")
    
    # Check if we have at least 8GB VRAM for comfortable quantization
    if total_memory < 8 * 1024**3:
        logging.warning("Limited GPU memory detected. Quantization may be slow or fail.")
    
    return True


def load_model(model_name: str, auto_class):
    """Try loading with a specific AutoModel class."""
    return auto_class.from_pretrained(
        model_name,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )


def download_and_quantize_gpu(model_name: str, bits: int = 8) -> tuple:
    """Download and quantize model using bitsandbytes on GPU."""
    logging.info(f"Downloading and quantizing model (GPU, {bits}-bit): {model_name}")
    
    if bits == 4:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
    else:
        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # Try AutoModelForCausalLM first, fall back to AutoModel
    for auto_class in [AutoModelForCausalLM, AutoModel]:
        try:
            logging.info(f"Trying {auto_class.__name__}...")
            model = auto_class.from_pretrained(
                model_name,
                device_map="auto",
                quantization_config=quantization_config,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
            logging.info(f"Model loaded and quantized with {auto_class.__name__}")
            return model, tokenizer
        except (ValueError, TypeError) as e:
            logging.warning(f"{auto_class.__name__} failed: {e}")
            continue
    
    raise RuntimeError(f"Could not load model {model_name} with any supported AutoModel class")


def download_and_quantize_cpu(model_name: str) -> tuple:
    """Download model and quantize weights to FP8 on CPU."""
    logging.info(f"Downloading and quantizing model (CPU): {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # Load model in float16 to reduce memory
    model = None
    for auto_class in [AutoModelForCausalLM, AutoModel]:
        try:
            logging.info(f"Trying {auto_class.__name__}...")
            model = auto_class.from_pretrained(
                model_name,
                dtype=torch.float16,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
            logging.info(f"Model loaded with {auto_class.__name__}")
            break
        except (ValueError, TypeError) as e:
            logging.warning(f"{auto_class.__name__} failed: {e}")
            continue
    
    if model is None:
        raise RuntimeError(f"Could not load model {model_name} with any supported AutoModel class")
    
    # Cast linear layer weights to float8_e4m3fn
    logging.info("Casting linear layer weights to float8_e4m3fn...")
    fp8_dtype = torch.float8_e4m3fn
    converted = 0
    for name, module in model.named_modules():
        if isinstance(module, torch.nn.Linear):
            module.weight.data = module.weight.data.to(fp8_dtype)
            converted += 1
    logging.info(f"Converted {converted} linear layers to FP8")
    
    return model, tokenizer


def _convert_shard_to_fp8(shard_path: Path, output_path: Path) -> None:
    """Load a single safetensors shard, cast weight tensors to FP8, and save."""
    fp8_dtype = torch.float8_e4m3fn
    tensors = safetensors_load(str(shard_path))
    converted = 0
    for key in tensors:
        # Only convert weight matrices (2-D), skip biases, norms, embeddings etc.
        if tensors[key].ndim == 2 and "weight" in key:
            tensors[key] = tensors[key].to(fp8_dtype)
            converted += 1
    safetensors_save(tensors, str(output_path))
    del tensors  # free memory immediately
    logging.info(f"  {shard_path.name}: converted {converted} tensors to FP8")


def download_and_quantize_low_memory(model_name: str, save_path: str, bits: int = 8) -> None:
    """Download model files and quantize shard-by-shard to minimize RAM usage.
    
    Instead of loading the full model into memory, this:
    1. Downloads the raw model files to a cache directory
    2. Processes each safetensors shard individually (only one shard in RAM at a time)
    3. Copies config, tokenizer, and other non-weight files as-is
    """
    logging.info(f"Low-memory quantization: {model_name}")
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    
    # Download all model files to local cache
    logging.info("Downloading model files...")
    model_dir = Path(snapshot_download(
        repo_id=model_name,
        allow_patterns=["*.safetensors", "*.json", "*.txt", "*.model", "*.jinja", "*.py"],
    ))
    logging.info(f"Model files cached at: {model_dir}")
    
    # Find safetensors shards
    shard_files = sorted(model_dir.glob("*.safetensors"))
    if not shard_files:
        raise FileNotFoundError(
            f"No .safetensors files found in {model_dir}. "
            "Low-memory mode only supports safetensors format."
        )
    
    logging.info(f"Found {len(shard_files)} safetensors shard(s). Converting to FP8 ({bits}-bit)...")
    
    # Process each shard one at a time
    for shard_file in shard_files:
        output_file = save_path / shard_file.name
        _convert_shard_to_fp8(shard_file, output_file)
    
    # Copy all non-safetensors files (config, tokenizer, index, etc.)
    for src_file in model_dir.iterdir():
        if src_file.is_file() and not src_file.name.endswith(".safetensors"):
            dst_file = save_path / src_file.name
            shutil.copy2(str(src_file), str(dst_file))
            logging.debug(f"Copied {src_file.name}")
    
    # Save quantization info
    quant_info = {
        "quantization": "FP8",
        "source_model": model_name,
        "original_framework": "pytorch",
        "bits": bits,
        "method": "low_memory_shard_by_shard"
    }
    with open(save_path / "quantization_info.json", "w") as f:
        json.dump(quant_info, f, indent=2)
    
    logging.info(f"Low-memory quantization complete. Output at: {save_path}")


def save_quantized_model(model, tokenizer, save_path: str, source_model: str, bits: int = 8) -> None:
    """Save quantized model and tokenizer locally."""
    logging.info(f"Saving quantized model to: {save_path}")
    
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)
    
    # Save model
    model.save_pretrained(save_path, safe_serialization=True)
    
    # Save tokenizer
    tokenizer.save_pretrained(save_path)
    
    quant_type = "FP8" if bits == 8 else "NF4"
    # Save quantization info
    quant_info = {
        "quantization": quant_type,
        "source_model": source_model,
        "original_framework": "pytorch",
        "bits": bits
    }
    
    with open(save_path / "quantization_info.json", "w") as f:
        json.dump(quant_info, f, indent=2)
    
    logging.info("Model saved successfully")


def upload_to_huggingface(
    model_path: str,
    repo_name: str,
    token: Optional[str] = None,
    private: bool = False,
    commit_message: str = "Upload quantized model"
) -> None:
    """Upload quantized model to Hugging Face."""
    logging.info(f"Uploading to Hugging Face repository: {repo_name}")
    
    api = HfApi(token=token)
    
    try:
        # Create repository if it doesn't exist
        create_repo(
            repo_id=repo_name,
            token=token,
            private=private,
            exist_ok=True
        )
        
        # Upload all files in the model directory
        api.upload_folder(
            folder_path=model_path,
            repo_id=repo_name,
            commit_message=commit_message,
        )
        
        logging.info(f"Model uploaded successfully to: https://huggingface.co/{repo_name}")
        
    except Exception as e:
        logging.error(f"Failed to upload model: {e}")
        raise


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Download, quantize, and upload Hugging Face models"
    )
    
    parser.add_argument(
        "--model-name",
        required=True,
        help="Name of the model to download from Hugging Face"
    )
    
    parser.add_argument(
        "--output-repo",
        required=True,
        help="Name of the repository to upload the quantized model"
    )
    
    parser.add_argument(
        "--local-path",
        default="./quantized_model",
        help="Local path to save the quantized model"
    )
    
    parser.add_argument(
        "--token",
        help="Hugging Face API token (or set HF_TOKEN environment variable)"
    )
    
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create a private repository"
    )
    
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="Force CPU usage even if GPU is available"
    )
    
    parser.add_argument(
        "--low-memory",
        action="store_true",
        help="Process weight shards one at a time to minimize RAM usage (CPU only, slower)"
    )
    
    parser.add_argument(
        "--bits",
        type=int,
        default=8,
        choices=[4, 8],
        help="Quantization bit width: 8 for FP8, 4 for NF4 (default: 8). 4-bit requires GPU."
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip uploading to Hugging Face (only save locally)"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Check GPU availability
    use_gpu = not args.cpu_only and check_gpu_availability()
    
    # Get token from environment if not provided
    token = args.token or os.getenv("HF_TOKEN")
    if not token and not args.skip_upload:
        logging.warning(
            "No Hugging Face token provided. Set HF_TOKEN environment variable or use --token. "
            "Upload will likely fail."
        )
    
    # Validate: 4-bit requires GPU
    if args.bits == 4 and not use_gpu:
        logging.error("4-bit (NF4) quantization requires a GPU. Use --bits 8 for CPU quantization.")
        sys.exit(1)
    
    if args.bits == 4 and args.low_memory:
        logging.error("4-bit (NF4) quantization is not supported in low-memory mode. It requires loading via bitsandbytes on GPU.")
        sys.exit(1)
    
    try:
        # Download and quantize model
        if args.low_memory:
            logging.info(f"Using low-memory shard-by-shard quantization ({args.bits}-bit)")
            download_and_quantize_low_memory(args.model_name, args.local_path, args.bits)
        elif use_gpu:
            model, tokenizer = download_and_quantize_gpu(args.model_name, args.bits)
            save_quantized_model(model, tokenizer, args.local_path, args.model_name, args.bits)
        else:
            model, tokenizer = download_and_quantize_cpu(args.model_name)
            save_quantized_model(model, tokenizer, args.local_path, args.model_name, args.bits)
        
        # Upload to Hugging Face
        if not args.skip_upload:
            upload_to_huggingface(
                args.local_path,
                args.output_repo,
                token,
                args.private
            )
        else:
            logging.info(f"Skipping upload. Quantized model saved at: {args.local_path}")
        
        logging.info("Quantization process completed successfully!")
        
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
