#!/bin/bash

# Hugging Face file download script
# Usage: HF_TOKEN=your_token ./download_files.sh

# Check if HF_TOKEN is set
if [ -z "$HF_TOKEN" ]; then
    echo "Error: HF_TOKEN environment variable is not set"
    echo "Usage: HF_TOKEN=your_token ./download_files.sh"
    exit 1
fi

# Define files to download: format is "repo_id|file_path|destination_folder"
FILES=(
    "Comfy-Org/flux2-klein-9B|split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors|text_encoders"
    "black-forest-labs/FLUX.2-klein-9B|vae/diffusion_pytorch_model.safetensors|vae"
    "black-forest-labs/FLUX.2-klein-9b-nvfp4|flux-2-klein-9b-nvfp4.safetensors|diffusion_models"
)

# Download each file
for entry in "${FILES[@]}"; do
    # Split the entry by |
    IFS='|' read -r repo_id file_path dest_folder <<< "$entry"
    
    echo "Downloading: $file_path from $repo_id"
    echo "Destination: $dest_folder/"
    
    hf download "$repo_id" \
        "$file_path" \
        --local-dir "$dest_folder" \
        --token "$HF_TOKEN"
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully downloaded $file_path"
    else
        echo "✗ Failed to download $file_path"
    fi
    echo ""
done

echo "Download complete!"
