FROM bundenth/ray:latest AS build-image

RUN sudo apt update && sudo apt install bc wget -y

WORKDIR $HOME/workspace

COPY run_model.sh .
COPY requirements.txt .

RUN . $HOME/workspace/env/bin/activate && \
    pip3 install -r requirements.txt --no-cache-dir

RUN sudo chmod +x $HOME/workspace/run_model.sh

CMD . $HOME/workspace/env/bin/activate
