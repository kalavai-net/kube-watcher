FROM ghcr.io/kalavai-net/ray-base:latest AS base

FROM lmsysorg/sglang:v0.5.9-cu130

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /home/ray/workspace

# copy over ray scripts
COPY --from=base /home/ray/workspace/ .

# RUN apt update && apt install bc wget -y && \
#     rm -rf /var/lib/apt/lists/*

COPY common_requirements.txt .
RUN pip install -r common_requirements.txt --no-cache-dir

COPY run_model.sh .
RUN chmod +x /home/ray/workspace/run_model.sh

