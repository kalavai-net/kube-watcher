#!/usr/bin/env python3
"""
Quick test script for quantized models.

Loads a quantized model from a local path or Hugging Face repo
and runs a simple text generation to verify it works.
"""

import argparse
import logging
import sys
import time

import torch
from transformers import AutoModelForCausalLM, AutoModel, AutoTokenizer


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_model(model_path: str):
    """Load model trying CausalLM first, then generic AutoModel."""
    for auto_class in [AutoModelForCausalLM, AutoModel]:
        try:
            logging.info(f"Trying {auto_class.__name__}...")
            model = auto_class.from_pretrained(
                model_path,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
            )
            logging.info(f"Loaded with {auto_class.__name__}")
            return model
        except (ValueError, TypeError) as e:
            logging.debug(f"{auto_class.__name__} failed: {e}")
            continue
    raise RuntimeError(f"Could not load model from {model_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Test a quantized model with a simple generation"
    )
    parser.add_argument(
        "--model-path",
        required=True,
        help="Local path or HF repo of the quantized model"
    )
    parser.add_argument(
        "--prompt",
        default="The meaning of life is",
        help="Prompt for text generation (default: 'The meaning of life is')"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=50,
        help="Maximum number of tokens to generate (default: 50)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    # Load tokenizer
    logging.info(f"Loading tokenizer from: {args.model_path}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)

    # Load model
    logging.info(f"Loading model from: {args.model_path}")
    t0 = time.time()
    model = load_model(args.model_path)
    load_time = time.time() - t0
    logging.info(f"Model loaded in {load_time:.1f}s")

    # Print model info
    param_count = sum(p.numel() for p in model.parameters())
    dtypes = {str(p.dtype) for p in model.parameters()}
    logging.info(f"Parameters: {param_count / 1e6:.1f}M")
    logging.info(f"Dtypes in model: {dtypes}")

    # Tokenize
    inputs = tokenizer(args.prompt, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    # Generate
    logging.info(f"Generating with prompt: '{args.prompt}'")
    t0 = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=args.max_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
    gen_time = time.time() - t0
    new_tokens = outputs.shape[1] - inputs["input_ids"].shape[1]

    # Decode and print
    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print("\n" + "=" * 60)
    print("GENERATED TEXT:")
    print("=" * 60)
    print(generated_text)
    print("=" * 60)
    print(f"\nTokens generated: {new_tokens}")
    print(f"Generation time:  {gen_time:.2f}s")
    if new_tokens > 0:
        print(f"Speed:            {new_tokens / gen_time:.1f} tokens/s")
    print()


if __name__ == "__main__":
    main()
