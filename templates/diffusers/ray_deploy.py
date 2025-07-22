"""
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
import torch

from ray import serve
from ray.serve.handle import DeploymentHandle


app = FastAPI()

# add models from HF https://huggingface.co/models?library=diffusers&sort=trending
supported_models = [
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
    "CompVis/stable-diffusion-v1-4",
    "black-forest-labs/FLUX.1-dev"
]
DEVICE = os.environ.get("DEVICE", "cuda")
NUM_GPUS = os.environ.get("NUM_GPUS", 1)
MIN_REPLICAS = os.environ.get("MIN_REPLICAS", 0)
MAX_REPLICAS = os.environ.get("MAX_REPLICAS", 1)


# OpenAI-compatible request models
class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="A text description of the desired image")
    model: str = Field(default="stable-diffusion-v1-5", description="The model to use for image generation")
    n: int = Field(default=1, ge=1, le=10, description="The number of images to generate")
    size: str = Field(default="1024x1024", description="The size of the generated images")
    quality: str = Field(default="standard", description="The quality of the image")
    response_format: str = Field(default="b64_json", description="The format in which the generated images are returned")
    style: Optional[str] = Field(default=None, description="The style of the generated images")
    user: Optional[str] = Field(default=None, description="A unique identifier representing your end-user")


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

    @app.get(
        "/imagine",
        responses={200: {"content": {"image/png": {}}}},
        response_class=Response,
    )
    async def generate(self, prompt: str, img_size: int = 512):
        assert len(prompt), "prompt parameter cannot be empty"

        image = await self.handle.generate.remote(prompt, img_size=img_size)
        file_stream = BytesIO()
        image.save(file_stream, "PNG")
        return Response(content=file_stream.getvalue(), media_type="image/png")

    @app.post("/v1/images/generations", response_model=ImageGenerationResponse)
    async def image_generation(self, request: ImageGenerationRequest):
        """OpenAI-compatible image generation endpoint"""
        if request.model not in supported_models:
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
            
            # Generate images
            images = []
            for _ in range(request.n):
                image = await self.handle.generate.remote(request.model, request.prompt, img_size=width)
                images.append(image)
            
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
            for model in supported_models
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
        # scheduler = EulerDiscreteScheduler.from_pretrained(
        #     model_id, subfolder="scheduler"
        # )
        self.current_model = None
        
    def load_model(self, model_id: str):
        if self.current_model != model_id:
            from diffusers import EulerDiscreteScheduler, StableDiffusionPipeline, FluxPipeline
            self.pipe = StableDiffusionPipeline.from_pretrained(
                model_id,
                #scheduler=scheduler,
                #revision="fp16",
                torch_dtype=torch.float16
            )
            #self.pipe = FluxPipeline.from_pretrained(model_id, torch_dtype=torch.bfloat16)
            if DEVICE == "cpu":
                self.pipe.enable_model_cpu_offload()
            else:
                self.pipe = self.pipe.to(DEVICE)
            self.current_model = model_id

    def generate(self, model_id: str, prompt: str, img_size: int = 512):
        assert len(model_id), "Model not loaded"
        assert len(prompt), "prompt parameter cannot be empty"
        self.load_model(model_id)

        with torch.autocast(DEVICE):
            image = self.pipe(prompt, height=img_size, width=img_size).images[0]
            return image


entrypoint = APIIngress.bind(StableDiffusionV2.bind())