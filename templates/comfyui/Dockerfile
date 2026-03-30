FROM nvidia/cuda:13.0.2-cudnn-devel-ubuntu24.04

RUN apt update && apt install wget git libgl1 libglib2.0-0 python3 python3-pip python3-venv -y

WORKDIR /workspace

RUN python3 -m venv /workspace/venv

ENV PATH="/workspace/venv/bin:$PATH"

RUN pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu130 --no-cache-dir

RUN git clone https://github.com/comfyanonymous/ComfyUI && \
    cd ComfyUI && \
    pip install -r requirements.txt --no-cache-dir

WORKDIR /workspace/ComfyUI

CMD [ "python", "main.py" ]
