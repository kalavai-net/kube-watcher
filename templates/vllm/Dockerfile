FROM bundenth/ray:latest AS build-image

RUN sudo apt update && sudo apt install bc wget ffmpeg curl -y

WORKDIR $HOME/workspace

COPY run_model.sh .
COPY requirements.txt .

# CUDA for LMCache
# RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
#     && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
#     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
#     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
# RUN sudo sed -i -e '/experimental/ s/^#//g' /etc/apt/sources.list.d/nvidia-container-toolkit.list
# RUN sudo apt-get update
# RUN sudo apt-get install -y nvidia-container-toolkit

# install dependencies
RUN . $HOME/workspace/env/bin/activate && \
    pip3 install -r requirements.txt --no-cache-dir && \
    pip3 install lmcache --prefer-binary --no-cache-dir

# install torchdec https://github.com/QwenLM/Qwen2.5-VL?tab=readme-ov-file#installing-cuda-enabled-torchcodec 
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
RUN pip3 install torchcodec --index-url=https://download.pytorch.org/whl/cu118

RUN sudo chmod +x $HOME/workspace/run_model.sh

CMD . $HOME/workspace/env/bin/activate
