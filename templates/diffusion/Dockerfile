FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

RUN apt update && apt install wget git libgl1 libglib2.0-0 python3 python3-pip python3-venv -y

WORKDIR /workspace

RUN git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git && \
    cd stable-diffusion-webui && \
    pip3 install -r requirements.txt --no-cache-dir

WORKDIR /workspace/stable-diffusion-webui

COPY download_model.py .

CMD [ "python3", "webui.py" ]
