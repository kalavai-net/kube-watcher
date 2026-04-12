"""
Text Encoder API Server for Modular Flux 2 Klein Pipeline

This server provides a REST API endpoint for text encoding that can be called
by the RemoteTextEncoderBlock in the modular pipeline.

Run with:
    python api_text_encoder_server.py

Or with custom settings:
    PORT=8001 DEVICE=cuda python api_text_encoder_server.py
"""

import os
import base64
import numpy as np
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import uvicorn

app = FastAPI(title="Text Encoder API", version="1.0.0")

PORT = int(os.environ.get("PORT", 8001))
DEVICE = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
MODEL_ID = os.environ.get("MODEL_ID", "black-forest-labs/FLUX.2-klein-4B")


class EncodeRequest(BaseModel):
    prompt: str
    prompt_2: Optional[str] = None
    max_sequence_length: int = 512


class EncodeResponse(BaseModel):
    prompt_embeds: str
    prompt_embeds_shape: list
    pooled_prompt_embeds: str
    pooled_prompt_embeds_shape: list


class TextEncoderService:
    def __init__(self, model_id: str, device: str):
        self.device = device
        self.model_id = model_id
        self.text_encoder = None
        self.text_encoder_2 = None
        self.tokenizer = None
        self.tokenizer_2 = None
        self._load_models()
    
    def _load_models(self):
        print(f"Loading text encoder from {self.model_id}...")
        
        from transformers import CLIPTextModel, CLIPTokenizer, T5EncoderModel, T5TokenizerFast
        
        try:
            self.tokenizer = CLIPTokenizer.from_pretrained(
                self.model_id, 
                subfolder="tokenizer",
                torch_dtype=torch.bfloat16
            )
            self.text_encoder = CLIPTextModel.from_pretrained(
                self.model_id,
                subfolder="text_encoder",
                torch_dtype=torch.bfloat16
            ).to(self.device)
            
            self.tokenizer_2 = T5TokenizerFast.from_pretrained(
                self.model_id,
                subfolder="tokenizer_2",
                torch_dtype=torch.bfloat16
            )
            self.text_encoder_2 = T5EncoderModel.from_pretrained(
                self.model_id,
                subfolder="text_encoder_2",
                torch_dtype=torch.bfloat16
            ).to(self.device)
            
            print(f"Text encoders loaded successfully on {self.device}")
            
        except Exception as e:
            print(f"Error loading text encoders: {e}")
            raise
    
    @torch.no_grad()
    def encode(self, prompt: str, prompt_2: Optional[str] = None, max_sequence_length: int = 512):
        if prompt_2 is None:
            prompt_2 = prompt
        
        text_inputs = self.tokenizer(
            prompt,
            padding="max_length",
            max_length=max_sequence_length,
            truncation=True,
            return_tensors="pt",
        )
        
        text_input_ids = text_inputs.input_ids.to(self.device)
        
        prompt_embeds = self.text_encoder(text_input_ids, output_hidden_states=False)
        pooled_prompt_embeds = prompt_embeds.pooler_output
        prompt_embeds = prompt_embeds.last_hidden_state
        
        text_inputs_2 = self.tokenizer_2(
            prompt_2,
            padding="max_length",
            max_length=max_sequence_length,
            truncation=True,
            return_tensors="pt",
        )
        
        text_input_ids_2 = text_inputs_2.input_ids.to(self.device)
        
        prompt_embeds_2 = self.text_encoder_2(text_input_ids_2, output_hidden_states=False)
        prompt_embeds_2 = prompt_embeds_2.last_hidden_state
        
        prompt_embeds = torch.cat([prompt_embeds, prompt_embeds_2], dim=-1)
        
        return prompt_embeds, pooled_prompt_embeds


text_encoder_service = TextEncoderService(MODEL_ID, DEVICE)


@app.post("/encode", response_model=EncodeResponse)
async def encode_text(request: EncodeRequest):
    """
    Encode text prompt into embeddings.
    
    Returns base64-encoded numpy arrays for prompt_embeds and pooled_prompt_embeds.
    """
    try:
        prompt_embeds, pooled_prompt_embeds = text_encoder_service.encode(
            prompt=request.prompt,
            prompt_2=request.prompt_2,
            max_sequence_length=request.max_sequence_length
        )
        
        prompt_embeds_np = prompt_embeds.cpu().numpy().astype(np.float32)
        pooled_embeds_np = pooled_prompt_embeds.cpu().numpy().astype(np.float32)
        
        prompt_embeds_b64 = base64.b64encode(prompt_embeds_np.tobytes()).decode('utf-8')
        pooled_embeds_b64 = base64.b64encode(pooled_embeds_np.tobytes()).decode('utf-8')
        
        return EncodeResponse(
            prompt_embeds=prompt_embeds_b64,
            prompt_embeds_shape=list(prompt_embeds_np.shape),
            pooled_prompt_embeds=pooled_embeds_b64,
            pooled_prompt_embeds_shape=list(pooled_embeds_np.shape)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Encoding failed: {str(e)}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "device": DEVICE,
        "model_id": MODEL_ID
    }


if __name__ == "__main__":
    print(f"Starting Text Encoder API server on port {PORT}")
    print(f"Device: {DEVICE}")
    print(f"Model: {MODEL_ID}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
