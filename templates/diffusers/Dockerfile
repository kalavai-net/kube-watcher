FROM bundenth/ray:latest AS build-image

RUN sudo apt update && sudo apt install bc wget ffmpeg curl -y

WORKDIR $HOME/workspace

COPY run_model.sh .
COPY requirements.txt .
COPY ray_deploy.py .

# install dependencies
#pip3 install lmcache --prefer-binary --no-cache-dir && \
RUN . $HOME/workspace/env/bin/activate && \
    pip3 install -r requirements.txt --no-cache-dir

RUN sudo chmod +x $HOME/workspace/run_model.sh

CMD . $HOME/workspace/env/bin/activate
