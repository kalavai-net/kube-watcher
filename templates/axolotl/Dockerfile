FROM bundenth/ray:latest AS build-image

RUN sudo apt update && sudo apt install bc wget ffmpeg curl -y

WORKDIR $HOME/workspace

COPY run_training.sh .
COPY requirements.txt .
COPY fine_tune.py .

# install dependencies
RUN . $HOME/workspace/env/bin/activate && \
    pip3 install -r requirements.txt --no-cache-dir

RUN sudo chmod +x $HOME/workspace/run_training.sh


# TEST HARNESS
COPY examples/axolotl_config.yaml .
COPY examples/dataset.jsonl .


CMD . $HOME/workspace/env/bin/activate
