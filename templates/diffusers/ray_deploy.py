"""
TODO: support AutoPipelineForImage2Image, AutoPipelineForInpainting
https://learnopencv.com/hugging-face-diffusers/

Serve:

serve run ray_deploy:entrypoint

Then send requests with

python ray_inference.py
"""
import os
import base64
import time
from datetime import datetime
from typing import List, Optional
from io import BytesIO
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from enum import Enum

import torch
from diffusers import (
    AutoPipelineForText2Image,
    StableDiffusionPipeline,
    FluxPipeline,
    Flux2KleinPipeline,
    EulerAncestralDiscreteScheduler,
    DPMSolverMultistepScheduler,
    UniPCMultistepScheduler,
    LCMScheduler
)
import ray
from ray import serve
from ray.serve.handle import DeploymentHandle


app = FastAPI()

class SchedulerEnum(str, Enum):
    euler_ancestral = "euler_ancestral"
    dpmpp_2m = "dpmpp_2m" 
    unipc = "unipc"
    lcm = "lcm"

# move to AutoPipeline https://huggingface.co/docs/diffusers/en/tutorials/autopipeline
#   supports Stable Diffusion, Stable Diffusion XL, ControlNet, Kandinsky 2.1, Kandinsky 2.2, and DeepFloyd IF
# add models from HF https://huggingface.co/models?library=diffusers&sort=trending
supported_models = {
    "stable-diffusion-v1-5/stable-diffusion-v1-5": AutoPipelineForText2Image,
    "CompVis/stable-diffusion-v1-4": AutoPipelineForText2Image,
    "black-forest-labs/FLUX.1-dev": FluxPipeline,
    "black-forest-labs/FLUX.2-klein-4B": Flux2KleinPipeline
}
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
DEVICE = os.environ.get("DEVICE", "cuda")
NUM_GPUS = int(os.environ.get("NUM_GPUS", 1))
MIN_REPLICAS = int(os.environ.get("MIN_REPLICAS", 0))
MAX_REPLICAS = int(os.environ.get("MAX_REPLICAS", 1))


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
    scheduler: SchedulerEnum = Field(default=SchedulerEnum.euler_ancestral, description="Scheduler to use for faster generation")
    compile: bool = Field(default=True, description="Whether to compile the pipeline for faster inference")
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
            
            while remaining_images > 0:
                current_batch_size = min(request.batch_size, remaining_images)
                
                # Generate batch of images
                batch_images = await self.handle.generate.remote(
                    model_id=request.model, 
                    prompt=request.prompt, 
                    height=height, 
                    width=width, 
                    num_images=current_batch_size,
                    scheduler=request.scheduler,
                    compile=request.compile,
                    **request.extra
                )
                images.extend(batch_images)
                remaining_images -= current_batch_size
            
            # Convert images to requested format
            data = []
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
    ray_actor_options={"num_gpus": NUM_GPUS},
    autoscaling_config={"min_replicas": MIN_REPLICAS, "max_replicas": MAX_REPLICAS},
)
class StableDiffusionV2:
    def __init__(self):
        self.current_model = None
        self.current_scheduler = None
        self.compiled_pipe = None
        
        # Available schedulers for faster generation
        self.schedulers = {
            SchedulerEnum.euler_ancestral: EulerAncestralDiscreteScheduler,
            SchedulerEnum.dpmpp_2m: DPMSolverMultistepScheduler,
            SchedulerEnum.unipc: UniPCMultistepScheduler,
            SchedulerEnum.lcm: LCMScheduler
        }
        
    def load_model(self, model_id: str, scheduler_name: SchedulerEnum = SchedulerEnum.euler_ancestral, compile: bool = True):
        if self.current_model != model_id or self.current_scheduler != scheduler_name:
            
            # Load pipeline
            self.pipe = supported_models[model_id].from_pretrained(
                model_id,
                torch_dtype=torch.float16,
                use_safetensors=True
            )
            
            # Set faster scheduler
            if scheduler_name in self.schedulers:
                self.pipe.scheduler = self.schedulers[scheduler_name].from_config(self.pipe.scheduler.config)
            
            if DEVICE == "cpu":
                self.pipe.enable_model_cpu_offload()
            else:
                self.pipe = self.pipe.to(DEVICE)
            
            # Memory optimizations
            self.pipe.enable_attention_slicing()
            if hasattr(self.pipe, 'enable_vae_slicing'):
                self.pipe.enable_vae_slicing()
            
            # Enable CPU for VAE when using CUDA to save memory
            if DEVICE == "cuda" and hasattr(self.pipe, 'enable_sequential_cpu_offload'):
                self.pipe.enable_sequential_cpu_offload()
            
            # Compile pipeline for faster inference
            if compile and DEVICE == "cuda":
                try:
                    print("Compiling pipeline for faster inference...")
                    self.compiled_pipe = torch.compile(self.pipe, mode="reduce-overhead", fullgraph=True)
                except Exception as e:
                    print(f"Compilation failed: {e}, using uncompiled pipeline")
                    self.compiled_pipe = self.pipe
            else:
                self.compiled_pipe = self.pipe
            
            self.current_model = model_id
            self.current_scheduler = scheduler_name

    def generate(self, model_id: str, prompt: str, num_images: int = 1, **kwargs):
        """Generate one or more images with optimized performance"""
        assert len(model_id), "Model not loaded"
        assert len(prompt), "prompt parameter cannot be empty"
        
        scheduler_name = kwargs.pop('scheduler', SchedulerEnum.euler_ancestral)
        compile = kwargs.pop('compile', True)
        
        self.load_model(model_id, scheduler_name, compile)
        
        # Use compiled pipeline if available
        pipe = self.compiled_pipe if self.compiled_pipe else self.pipe
        
        # Optimize inference parameters for speed
        generation_kwargs = {
            'prompt': [prompt] * num_images if num_images > 1 else prompt,
            **kwargs
        }
        
        # Use LCM scheduler for ultra-fast generation if requested
        if scheduler_name == SchedulerEnum.lcm:
            generation_kwargs['num_inference_steps'] = kwargs.get('num_inference_steps', 4)
            generation_kwargs['guidance_scale'] = kwargs.get('guidance_scale', 1.0)
        
        with torch.autocast(DEVICE):
            images = pipe(**generation_kwargs).images
            return images[0] if num_images == 1 else images

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