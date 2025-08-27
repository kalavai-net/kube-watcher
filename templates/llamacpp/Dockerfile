# syntax=docker/dockerfile:1
#FROM debian:bullseye AS builder
FROM python:3.10-slim AS builder

RUN apt-get update && apt-get install --yes git cmake g++ libgomp1 iputils-ping wget curl && \
    rm -rf /var/lib/apt/lists/*

COPY common_requirements.txt .
RUN pip install -r common_requirements.txt --no-cache-dir && \
    rm -rf /home/ray/.cache/pip

WORKDIR /workspace
RUN git clone https://github.com/ggerganov/llama.cpp.git

COPY run_rpc_worker.sh .
COPY run_api_server.sh .
COPY build.sh .
COPY get_workers_address.sh .
COPY merge.sh .
COPY generate_config.py .

RUN chmod +x /workspace/merge.sh
RUN chmod +x /workspace/run_rpc_worker.sh
RUN chmod +x /workspace/run_api_server.sh
RUN chmod +x /workspace/build.sh
RUN chmod +x /workspace/get_workers_address.sh
