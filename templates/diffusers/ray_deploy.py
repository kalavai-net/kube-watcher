"""
https://learnopencv.com/hugging-face-diffusers/

Serve:

serve run ray_deploy:entrypoint

Then send requests with

python ray_inference.py
"""
import os
import base64
import time
import logging
from datetime import datetime
from typing import List, Optional
from io import BytesIO
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import torch
import ray
from ray import serve
from ray.serve.handle import DeploymentHandle
from diffusers import (
    AutoPipelineForText2Image,
    FluxPipeline,
    Flux2KleinPipeline,
)

from diffusers.quantizers import PipelineQuantizationConfig


###############################
###############################
def load_pipeline(model_class, model_id: str, device: str, dtype: torch.dtype = torch.float16, quantization: bool = False, compile_mode: str = None):
    # Load pipeline
    load_kwargs = {
        "use_safetensors": True,
        "torch_dtype": dtype
    }
        
    if quantization:
        load_kwargs["quantization_config"] = PipelineQuantizationConfig(
            quant_backend="bitsandbytes_4bit",
            quant_kwargs={
                "load_in_4bit": True, 
                "bnb_4bit_quant_type": "nf4", 
                "bnb_4bit_compute_dtype": dtype
            },
            components_to_quantize=[
                "transformer",
                "text_encoder_2",
                "text_encoder",
                "vae",  # Enable VAE quantization to save VRAM
            ]
        )
    
    pipe = model_class.from_pretrained(
        model_id,
        low_cpu_mem_usage=True,
        **load_kwargs
    )

    # graph optimisation (requires compilation when model changes)
    if hasattr(pipe, 'transformer') and compile_mode is not None:
        match compile_mode:
            case "reduce-overhead":
                # OPTION A: The Balanced Approach (Recommended)
                # Fast to compile (~1-2 min), solid 15-20% speedup.
                pipe.transformer = torch.compile(pipe.transformer, mode="reduce-overhead")
            case "max-autotune":
                # OPTION B: The Maximum Speed Approach
                # Slow to compile (~5 min), up to 30-40% speedup on RTX 40/50 series.
                # This uses Triton kernels and CUDA graphs.
                pipe.transformer = torch.compile(pipe.transformer, mode="max-autotune")
            case "regional":
                # OPTION C: regional compilation, single block. Best trade off speed vs gen time
                pipe.transformer.compile_repeated_blocks(fullgraph=True, dynamic=True)
    
    if device == "cuda":
        pipe = pipe.to(device)
    
    # Enable VAE tiling for high-resolution images to reduce memory usage
    if hasattr(pipe, 'vae'):
        pipe.vae.enable_tiling()
    
    return pipe

###############################
###############################

app = FastAPI()

# move to AutoPipeline https://huggingface.co/docs/diffusers/en/tutorials/autopipeline
#   supports Stable Diffusion, Stable Diffusion XL, ControlNet, Kandinsky 2.1, Kandinsky 2.2, and DeepFloyd IF
# add models from HF https://huggingface.co/models?library=diffusers&sort=trending
supported_models = {
    "stable-diffusion-v1-5/stable-diffusion-v1-5": {
        "class": AutoPipelineForText2Image,
        "fn": load_pipeline
    },
    "CompVis/stable-diffusion-v1-4": {
        "class": AutoPipelineForText2Image,
        "fn": load_pipeline
    },
    "black-forest-labs/FLUX.1-dev": {
        "class": FluxPipeline,
        "fn": load_pipeline
    },
    "black-forest-labs/FLUX.2-klein-4B": {
        "class": Flux2KleinPipeline,
        "fn": load_pipeline
    },
    "black-forest-labs/FLUX.2-klein-9B": {
        "class": Flux2KleinPipeline,
        "fn": load_pipeline
    }
}

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
DEVICE = os.environ.get("DEVICE", "cpu")
NUM_GPUS = int(os.environ.get("NUM_GPUS", 1))
MIN_REPLICAS = int(os.environ.get("MIN_REPLICAS", 0))
MAX_REPLICAS = int(os.environ.get("MAX_REPLICAS", 1))
QUANTIZATION = os.environ.get("QUANTIZATION", "false").lower() == "true"
COMPILE_MODE = os.environ.get("COMPILE_MODE", None)


# OpenAI-compatible request models
class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="A text description of the desired image")
    model: str = Field(default="stable-diffusion-v1-5", description="The model to use for image generation")
    n: int = Field(default=1, ge=1, le=10, description="The number of images to generate")
    size: str = Field(default="512x512", description="The size of the generated images")
    quality: str = Field(default="standard", description="The quality of the image")
    response_format: str = Field(default="b64_json", description="The format in which the generated images are returned")
    style: Optional[str] = Field(default=None, description="The style of the generated images")
    user: Optional[str] = Field(default=None, description="A unique identifier representing your end-user")
    extra: Optional[dict] = Field(default=None, description="Extra parameters for a diffusers pipeline")
    batch_size: int = Field(default=1, ge=1, le=4, description="Batch size for parallel generation")

class ImageEditRequest(BaseModel):
    image: str = Field(..., description="The image to edit")
    prompt: str = Field(..., description="A text description of the desired image")
    mask: Optional[str] = Field(default=None, description="An additional image whose fully transparent areas indicate where image should be edited")
    model: str = Field(default="stable-diffusion-v1-5", description="The model to use for image generation")
    n: int = Field(default=1, ge=1, le=10, description="The number of images to generate")
    size: str = Field(default="1024x1024", description="The size of the generated images")
    response_format: str = Field(default="b64_json", description="The format in which the generated images are returned")
    user: Optional[str] = Field(default=None, description="A unique identifier representing your end-user")


class ImageVariationRequest(BaseModel):
    image: str = Field(..., description="The image to use as the basis for the variation")
    model: str = Field(default="stable-diffusion-v1-5", description="The model to use for image generation")
    n: int = Field(default=1, ge=1, le=10, description="The number of images to generate")
    size: str = Field(default="1024x1024", description="The size of the generated images")
    response_format: str = Field(default="url", description="The format in which the generated images are returned")
    user: Optional[str] = Field(default=None, description="A unique identifier representing your end-user")


# OpenAI-compatible response models
class ImageData(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: List[ImageData]


class ErrorResponse(BaseModel):
    error: dict


@serve.deployment(num_replicas=1)
@serve.ingress(app)
class APIIngress:
    def __init__(self, diffusion_model_handle: DeploymentHandle) -> None:
        self.handle = diffusion_model_handle
        # Configure logger for this deployment
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    @app.post("/v1/images/generations", response_model=ImageGenerationResponse)
    async def image_generation(self, request: ImageGenerationRequest):
        """OpenAI-compatible image generation endpoint"""
        if False and request.model not in supported_models.keys():
            raise HTTPException(status_code=400, detail=f"Model {request.model} is not supported")
        try:
            # Parse size string (e.g., "1024x1024")
            size_parts = request.size.split("x")
            if len(size_parts) != 2:
                raise HTTPException(status_code=400, detail="Invalid size format. Use format like '1024x1024'")
            
            width = int(size_parts[0])
            height = int(size_parts[1])
            
            # Validate size constraints
            if width != height:
                raise HTTPException(status_code=400, detail="Only square images are supported")
            if width not in [256, 512, 1024]:
                raise HTTPException(status_code=400, detail="Size must be one of: 256, 512, 1024")
            
            # Generate images with batch processing
            images = []
            remaining_images = request.n
            
            t = time.time()
            while remaining_images > 0:
                current_batch_size = min(request.batch_size, remaining_images)
                
                # Generate batch of images
                batch_images = await self.handle.generate.remote(
                    model_id=request.model, 
                    prompt=request.prompt, 
                    height=height, 
                    width=width, 
                    num_images=current_batch_size,
                    **request.extra
                )
                images.extend(batch_images)
                remaining_images -= current_batch_size
            
            self.logger.info(f"--> Batch generation completed in {time.time() - t:.2f}s")
            
            # Convert images to requested format
            data = []
            t = time.time()
            for image in images:
                
                file_stream = BytesIO()
                image.save(file_stream, "PNG")
                if request.response_format == "url":
                    raise HTTPException(status_code=501, detail="URL response format is not yet implemented")
                elif request.response_format == "b64_json":
                    b64_data = base64.b64encode(file_stream.getvalue()).decode('utf-8')
                    data.append(ImageData(b64_json=b64_data))
                else:
                    raise HTTPException(status_code=400, detail="response_format must be 'url' or 'b64_json'")
            self.logger.info(f"--> Image conversion completed in {time.time() - t:.2f}s")
            return ImageGenerationResponse(
                created=int(time.time()),
                data=data
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/v1/images/edits", response_model=ImageGenerationResponse)
    async def image_edit(self, request: ImageEditRequest):
        """OpenAI-compatible image edit endpoint (not implemented yet)"""
        raise HTTPException(status_code=501, detail="Image editing is not yet implemented")

    @app.post("/v1/images/variations", response_model=ImageGenerationResponse)
    async def image_variation(self, request: ImageVariationRequest):
        """OpenAI-compatible image variation endpoint (not implemented yet)"""
        raise HTTPException(status_code=501, detail="Image variations are not yet implemented")

    @app.get("/v1/models")
    async def list_models(self):
        """List available models"""
        return {
            "object": "list",
            "data": [
                {
                    "id": model,
                    "object": "model",
                    "created": 1640995200,
                    "owned_by": "openai",
                    "permission": [],
                    "root": model,
                    "parent": None
                }
            for model in supported_models.keys()
            ]
        }

    @app.get("/health")
    async def health_check(self):
        """Health check endpoint"""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@serve.deployment(
    ray_actor_options={"num_gpus": NUM_GPUS if DEVICE == "cuda" else 0},
    autoscaling_config={"min_replicas": MIN_REPLICAS, "max_replicas": MAX_REPLICAS},
)
class StableDiffusionV2:
    def __init__(self):
        self.current_model = None
        
    def load_model(self, model_id: str):
        if self.current_model != model_id:

            self.pipe = supported_models[model_id]["fn"](
                model_id=model_id,
                model_class=supported_models[model_id]["class"],
                dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                quantization=QUANTIZATION,
                compile_mode=COMPILE_MODE,
                device=DEVICE
            )
            
            self.current_model = model_id

    def generate(self, model_id: str, prompt: str, num_images: int = 1, **kwargs):
        """Generate one or more images with optimized performance"""
        assert len(model_id), "Model not loaded"
        assert len(prompt), "prompt parameter cannot be empty"
        
        self.load_model(model_id)
        
        # Optimize inference parameters for speed
        generation_kwargs = {
            'prompt': [prompt] * num_images,  # Always pass as list
            'num_images_per_prompt': 1  # We handle multiple images via prompt list
        }
        
        if kwargs:
            generation_kwargs.update(kwargs)
        
        with torch.autocast(DEVICE):
            result = self.pipe(**generation_kwargs)
            images = result.images  # This is always a list
            
            # Always return a list, even for single images
            return images[:num_images]  # Return list of requested images


if __name__ == "__main__":
    entrypoint = APIIngress.bind(StableDiffusionV2.bind())

    # connect to cluster (if run on head node, connect to existing instance)
    ray.init(address="auto")
    # bind address
    serve.start(
        http_options={
            "host": HOST,
            "port": PORT
        }
    )
    # Serve deployments
    serve.run(
        entrypoint
    )

    while True:
        time.sleep(10)