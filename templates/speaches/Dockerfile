FROM python:3.12-slim

RUN apt update && apt install git wget curl -y

WORKDIR /workspace
RUN git clone https://github.com/speaches-ai/speaches.git
WORKDIR /workspace/speaches
RUN python -m pip install uv 
RUN uv venv && . .venv/bin/activate && uv sync --all-extras
RUN pip install huggingface_hub
ENV HF_HOME=/workspace/huggingface

# Download the ONNX model (~346 MBs)
ENV KOKORO_REVISION=c97b7bbc3e60f447383c79b2f94fee861ff156ac
RUN huggingface-cli download hexgrad/Kokoro-82M --include 'kokoro-v0_19.onnx' --revision $KOKORO_REVISION

# Download the voices.bin (~5.5 MBs) file
RUN curl --location --output $HF_HOME/hub/models--hexgrad--Kokoro-82M/snapshots/$KOKORO_REVISION/voices.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin

# Download all English voices (~4.5 minutes) - too much, rate limited
#RUNhuggingface-cli download rhasspy/piper-voices --include 'en/**/*' 'voices.json'
# Download specific voices
RUN huggingface-cli download rhasspy/piper-voices --include 'en/en_US/af/**/*' 'voices.json'
RUN huggingface-cli download rhasspy/piper-voices --include 'en/en_US/bm_george/**/*' 'voices.json'

#uvicorn --factory --host 0.0.0.0 speaches.main:create_app
