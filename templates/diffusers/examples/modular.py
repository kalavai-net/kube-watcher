"""
Flux 2 Klein Modular Pipeline with Remote API Components

This example demonstrates how to create a modular diffusion pipeline where:
- Transformer and Text Encoder use remote API calls (for distributed processing)
- VAE uses the default local component

This allows you to:
1. Reuse components across multiple pipelines
2. Load larger models without being limited to a single machine's capacity
3. Scale different components independently

Based on: https://huggingface.co/blog/modular-diffusers
"""

import torch
import requests
import numpy as np
from typing import Optional, Dict, Any, List
from io import BytesIO
import base64

from diffusers import ModularPipeline, ModularPipelineBlocks
from diffusers.blocks import ComponentSpec, InputParam, OutputParam
from diffusers.utils import logging

logger = logging.get_logger(__name__)


class RemoteTextEncoderBlock(ModularPipelineBlocks):
    """
    Custom block that calls a remote API for text encoding instead of running locally.
    This allows using larger text encoders or sharing them across multiple pipelines.
    """
    
    def __init__(self, api_endpoint: str, api_key: Optional[str] = None):
        super().__init__()
        self.api_endpoint = api_endpoint
        self.api_key = api_key
    
    @property
    def expected_components(self):
        return []
    
    @property
    def inputs(self):
        return [
            InputParam("prompt", required=True, description="Text prompt to encode"),
            InputParam("prompt_2", required=False, description="Secondary prompt (if supported)"),
            InputParam("max_sequence_length", required=False, default=512, description="Maximum sequence length"),
        ]
    
    @property
    def intermediate_outputs(self):
        return [
            OutputParam("prompt_embeds", type_hint=torch.Tensor, description="Encoded prompt embeddings"),
            OutputParam("pooled_prompt_embeds", type_hint=torch.Tensor, description="Pooled prompt embeddings"),
        ]
    
    @torch.no_grad()
    def __call__(self, components, state):
        block_state = self.get_block_state(state)
        
        prompt = block_state.prompt
        prompt_2 = getattr(block_state, "prompt_2", None)
        max_sequence_length = getattr(block_state, "max_sequence_length", 512)
        
        logger.info(f"Calling remote text encoder API at {self.api_endpoint}")
        
        payload = {
            "prompt": prompt,
            "max_sequence_length": max_sequence_length,
        }
        
        if prompt_2 is not None:
            payload["prompt_2"] = prompt_2
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.post(
                f"{self.api_endpoint}/encode",
                json=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            prompt_embeds = torch.tensor(
                np.frombuffer(base64.b64decode(result["prompt_embeds"]), dtype=np.float32)
            ).reshape(result["prompt_embeds_shape"])
            
            pooled_prompt_embeds = torch.tensor(
                np.frombuffer(base64.b64decode(result["pooled_prompt_embeds"]), dtype=np.float32)
            ).reshape(result["pooled_prompt_embeds_shape"])
            
            block_state.prompt_embeds = prompt_embeds.to(block_state.device)
            block_state.pooled_prompt_embeds = pooled_prompt_embeds.to(block_state.device)
            
            logger.info(f"Received embeddings: prompt_embeds shape={prompt_embeds.shape}, pooled shape={pooled_prompt_embeds.shape}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call remote text encoder API: {e}")
            raise RuntimeError(f"Remote text encoder API call failed: {e}")
        
        self.set_block_state(state, block_state)
        return components, state


class RemoteTransformerBlock(ModularPipelineBlocks):
    """
    Custom block that calls a remote API for transformer denoising.
    This allows using larger transformers or distributing the compute load.
    """
    
    def __init__(self, api_endpoint: str, api_key: Optional[str] = None):
        super().__init__()
        self.api_endpoint = api_endpoint
        self.api_key = api_key
    
    @property
    def expected_components(self):
        return [
            ComponentSpec("scheduler", required=True, description="Noise scheduler"),
        ]
    
    @property
    def inputs(self):
        return [
            InputParam("prompt_embeds", required=True, description="Text embeddings"),
            InputParam("pooled_prompt_embeds", required=True, description="Pooled text embeddings"),
            InputParam("num_inference_steps", required=False, default=4, description="Number of denoising steps"),
            InputParam("guidance_scale", required=False, default=0.0, description="Guidance scale"),
            InputParam("height", required=False, default=1024, description="Image height"),
            InputParam("width", required=False, default=1024, description="Image width"),
            InputParam("generator", required=False, description="Random generator for reproducibility"),
        ]
    
    @property
    def intermediate_outputs(self):
        return [
            OutputParam("latents", type_hint=torch.Tensor, description="Denoised latent representation"),
        ]
    
    @torch.no_grad()
    def __call__(self, components, state):
        block_state = self.get_block_state(state)
        
        prompt_embeds = block_state.prompt_embeds
        pooled_prompt_embeds = block_state.pooled_prompt_embeds
        num_inference_steps = getattr(block_state, "num_inference_steps", 4)
        guidance_scale = getattr(block_state, "guidance_scale", 0.0)
        height = getattr(block_state, "height", 1024)
        width = getattr(block_state, "width", 1024)
        
        logger.info(f"Calling remote transformer API at {self.api_endpoint}")
        
        prompt_embeds_b64 = base64.b64encode(
            prompt_embeds.cpu().numpy().astype(np.float32).tobytes()
        ).decode('utf-8')
        
        pooled_embeds_b64 = base64.b64encode(
            pooled_prompt_embeds.cpu().numpy().astype(np.float32).tobytes()
        ).decode('utf-8')
        
        payload = {
            "prompt_embeds": prompt_embeds_b64,
            "prompt_embeds_shape": list(prompt_embeds.shape),
            "pooled_prompt_embeds": pooled_embeds_b64,
            "pooled_prompt_embeds_shape": list(pooled_prompt_embeds.shape),
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "height": height,
            "width": width,
        }
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.post(
                f"{self.api_endpoint}/denoise",
                json=payload,
                headers=headers,
                timeout=300
            )
            response.raise_for_status()
            
            result = response.json()
            
            latents = torch.tensor(
                np.frombuffer(base64.b64decode(result["latents"]), dtype=np.float32)
            ).reshape(result["latents_shape"])
            
            block_state.latents = latents.to(block_state.device)
            
            logger.info(f"Received latents with shape: {latents.shape}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call remote transformer API: {e}")
            raise RuntimeError(f"Remote transformer API call failed: {e}")
        
        self.set_block_state(state, block_state)
        return components, state


def create_flux2_klein_modular_pipeline(
    text_encoder_api: str,
    transformer_api: str,
    api_key: Optional[str] = None,
    model_id: str = "black-forest-labs/FLUX.2-klein-4B"
):
    """
    Create a Flux 2 Klein modular pipeline with remote API components.
    
    Args:
        text_encoder_api: URL of the text encoder API endpoint
        transformer_api: URL of the transformer API endpoint
        api_key: Optional API key for authentication
        model_id: HuggingFace model ID for the base pipeline
    
    Returns:
        A configured modular pipeline ready for inference
    """
    
    pipe = ModularPipeline.from_pretrained(model_id)
    
    blocks = pipe.blocks
    
    remote_text_encoder = RemoteTextEncoderBlock(
        api_endpoint=text_encoder_api,
        api_key=api_key
    )
    blocks.sub_blocks["text_encoder"] = remote_text_encoder
    
    remote_transformer = RemoteTransformerBlock(
        api_endpoint=transformer_api,
        api_key=api_key
    )
    blocks.sub_blocks["denoise"] = remote_transformer
    
    custom_pipe = blocks.init_pipeline(model_id)
    
    custom_pipe.load_components(torch_dtype=torch.bfloat16)
    
    return custom_pipe


if __name__ == "__main__":
    TEXT_ENCODER_API = "http://localhost:8001"
    TRANSFORMER_API = "http://localhost:8002"
    API_KEY = None
    
    print("Creating Flux 2 Klein modular pipeline with remote components...")
    
    pipeline = create_flux2_klein_modular_pipeline(
        text_encoder_api=TEXT_ENCODER_API,
        transformer_api=TRANSFORMER_API,
        api_key=API_KEY,
        model_id="black-forest-labs/FLUX.2-klein-4B"
    )
    
    print("\nPipeline blocks:")
    print(pipeline.blocks)
    
    print("\nGenerating image...")
    image = pipeline(
        prompt="a serene landscape at sunset with mountains and a lake",
        num_inference_steps=4,
        height=1024,
        width=1024,
    ).images[0]
    
    image.save("output_modular.png")
    print("Image saved to output_modular.png")
