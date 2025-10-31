FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

RUN apt update && apt install wget git libgl1 libglib2.0-0 python3 python3-pip python3-venv -y

RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir

WORKDIR /workspace

RUN git clone https://github.com/comfyanonymous/ComfyUI && \
    cd ComfyUI && \
    pip install -r requirements.txt --no-cache-dir

WORKDIR /workspace/ComfyUI

CMD [ "python3", "main.py" ]
