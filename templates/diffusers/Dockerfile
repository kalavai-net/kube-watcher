FROM kalavai/ray-base:latest AS build-image

RUN apt update && apt install bc wget ffmpeg curl -y

WORKDIR /home/ray/workspace

COPY run_model.sh .
COPY requirements.txt .
COPY ray_deploy.py .

# install dependencies
#pip3 install lmcache --prefer-binary --no-cache-dir && \
RUN pip3 install -r requirements.txt --no-cache-dir

RUN chmod +x /home/ray/workspace/run_model.sh

