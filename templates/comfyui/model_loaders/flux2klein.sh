#!/bin/bash
# Run this scripts from ComfyUI/models directory

# flux2klein 4b
wget -P vae/ https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors
wget -P text_encoders/ https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors
wget -P diffusion_models/ https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/diffusion_models/flux-2-klein-4b.safetensors
#quants
wget -P diffusion_models/ https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-nvfp4/resolve/main/flux-2-klein-4b-nvfp4.safetensors

# flux2klein 9b
wget -P vae/ https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors
wget -P diffusion_models/ https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-nvfp4/resolve/main/flux-2-klein-9b-nvfp4.safetensors
wget -P text_encoders/ https://huggingface.co/Comfy-Org/flux2-klein-9B/resolve/main/split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors


#python merge.py model.safetensors.index.json -o qwen4b-fp8.safetensors