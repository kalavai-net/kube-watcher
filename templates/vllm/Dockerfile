FROM bundenth/ray:latest AS build-image

RUN sudo apt update && sudo apt install bc wget ffmpeg curl -y

WORKDIR $HOME/workspace

COPY run_model.sh .
COPY requirements.txt .

# install dependencies
#pip3 install lmcache --prefer-binary --no-cache-dir && \
RUN . $HOME/workspace/env/bin/activate && \
    pip3 install -r requirements.txt --no-cache-dir
    
# install torchdec https://github.com/QwenLM/Qwen2.5-VL?tab=readme-ov-file#installing-cuda-enabled-torchcodec 
#pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --no-cache-dir && \
RUN . $HOME/workspace/env/bin/activate && \
    pip3 install torchcodec --index-url=https://download.pytorch.org/whl/cu124 --no-cache-dir

RUN sudo chmod +x $HOME/workspace/run_model.sh

CMD . $HOME/workspace/env/bin/activate
