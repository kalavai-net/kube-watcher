# ComfyUI

https://docs.comfy.org/installation/manual_install



## installation

AMD and CUDA: https://github.com/comfyanonymous/ComfyUI?tab=readme-ov-file#manual-install-windows-linux


## Download models

Models are downloaded from the browser, but this downloads them in the local machine (not in the remote instance).

Models must be downloaded @ /workspace/Comfyui/models/

So we should map PVCs to:
- Models, outputs and settings to /workspace/Comfyui/models
- Output images to /workspace/Comfyui/output
- Settings and extra nodes to /workspace/Comfyui/user/default (rw)
- Saved workflows to /workspace/Comfyui/user/default/workflows (rw)


## Add custom nodes

https://docs.comfy.org/installation/install_custom_node


