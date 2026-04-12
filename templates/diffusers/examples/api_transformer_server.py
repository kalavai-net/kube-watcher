"""
Transformer API Server for Modular Flux 2 Klein Pipeline

This server provides a REST API endpoint for transformer denoising that can be called
by the RemoteTransformerBlock in the modular pipeline.

Run with:
    python api_transformer_server.py

Or with custom settings:
    PORT=8002 DEVICE=cuda python api_transformer_server.py
"""

import os
import base64
import numpy as np
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import uvicorn

app = FastAPI(title="Transformer API", version="1.0.0")

PORT = int(os.environ.get("PORT", 8002))
DEVICE = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
MODEL_ID = os.environ.get("MODEL_ID", "black-forest-labs/FLUX.2-klein-4B")


class DenoiseRequest(BaseModel):
    prompt_embeds: str
    prompt_embeds_shape: list
    pooled_prompt_embeds: str
    pooled_prompt_embeds_shape: list
    num_inference_steps: int = 4
    guidance_scale: float = 0.0
    height: int = 1024
    width: int = 1024


class DenoiseResponse(BaseModel):
    latents: str
    latents_shape: list


class TransformerService:
    def __init__(self, model_id: str, device: str):
        self.device = device
        self.model_id = model_id
        self.transformer = None
        self.scheduler = None
        self._load_models()
    
    def _load_models(self):
        print(f"Loading transformer from {self.model_id}...")
        
        from diffusers import FlowMatchEulerDiscreteScheduler
        from diffusers.models import FluxTransformer2DModel
        
        try:
            self.transformer = FluxTransformer2DModel.from_pretrained(
                self.model_id,
                subfolder="transformer",
                torch_dtype=torch.bfloat16
            ).to(self.device)
            
            self.scheduler = FlowMatchEulerDiscreteScheduler.from_pretrained(
                self.model_id,
                subfolder="scheduler"
            )
            
            print(f"Transformer loaded successfully on {self.device}")
            
        except Exception as e:
            print(f"Error loading transformer: {e}")
            raise
    
    @torch.no_grad()
    def denoise(
        self,
        prompt_embeds: torch.Tensor,
        pooled_prompt_embeds: torch.Tensor,
        num_inference_steps: int = 4,
        guidance_scale: float = 0.0,
        height: int = 1024,
        width: int = 1024,
    ):
        batch_size = prompt_embeds.shape[0]
        
        num_channels_latents = self.transformer.config.in_channels // 4
        latents_shape = (
            batch_size,
            num_channels_latents,
            height // 8,
            width // 8,
        )
        
        latents = torch.randn(latents_shape, device=self.device, dtype=torch.bfloat16)
        
        self.scheduler.set_timesteps(num_inference_steps, device=self.device)
        timesteps = self.scheduler.timesteps
        
        for i, t in enumerate(timesteps):
            latent_model_input = latents
            
            timestep = t.expand(latents.shape[0])
            
            noise_pred = self.transformer(
                hidden_states=latent_model_input,
                timestep=timestep,
                encoder_hidden_states=prompt_embeds,
                pooled_projections=pooled_prompt_embeds,
                return_dict=False,
            )[0]
            
            latents = self.scheduler.step(noise_pred, t, latents, return_dict=False)[0]
        
        return latents


transformer_service = TransformerService(MODEL_ID, DEVICE)


@app.post("/denoise", response_model=DenoiseResponse)
async def denoise_latents(request: DenoiseRequest):
    """
    Perform transformer denoising on the provided embeddings.
    
    Returns base64-encoded numpy array for the denoised latents.
    """
    try:
        prompt_embeds_bytes = base64.b64decode(request.prompt_embeds)
        prompt_embeds = torch.tensor(
            np.frombuffer(prompt_embeds_bytes, dtype=np.float32)
        ).reshape(request.prompt_embeds_shape).to(transformer_service.device)
        
        pooled_embeds_bytes = base64.b64decode(request.pooled_prompt_embeds)
        pooled_prompt_embeds = torch.tensor(
            np.frombuffer(pooled_embeds_bytes, dtype=np.float32)
        ).reshape(request.pooled_prompt_embeds_shape).to(transformer_service.device)
        
        latents = transformer_service.denoise(
            prompt_embeds=prompt_embeds,
            pooled_prompt_embeds=pooled_prompt_embeds,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            height=request.height,
            width=request.width,
        )
        
        latents_np = latents.cpu().numpy().astype(np.float32)
        latents_b64 = base64.b64encode(latents_np.tobytes()).decode('utf-8')
        
        return DenoiseResponse(
            latents=latents_b64,
            latents_shape=list(latents_np.shape)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Denoising failed: {str(e)}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "device": DEVICE,
        "model_id": MODEL_ID
    }


if __name__ == "__main__":
    print(f"Starting Transformer API server on port {PORT}")
    print(f"Device: {DEVICE}")
    print(f"Model: {MODEL_ID}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
