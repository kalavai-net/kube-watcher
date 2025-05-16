FROM bundenth/ray:latest AS build-image

RUN sudo apt update && sudo apt install bc wget ffmpeg -y

WORKDIR $HOME/workspace

COPY run_model.sh .
COPY requirements.txt .

RUN . $HOME/workspace/env/bin/activate && \
    pip3 install -r requirements.txt --no-cache-dir

# install torchdec https://github.com/QwenLM/Qwen2.5-VL?tab=readme-ov-file#installing-cuda-enabled-torchcodec 
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
RUN pip3 install torchcodec --index-url=https://download.pytorch.org/whl/cu118

RUN sudo chmod +x $HOME/workspace/run_model.sh

CMD . $HOME/workspace/env/bin/activate
