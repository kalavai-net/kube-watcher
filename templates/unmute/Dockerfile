# This is the public-facing version.
#FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS base
FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

# Set environment variables to avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHON_VERSION=3.10.1
ENV PYTHON_MAJOR=3

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    ca-certificates \
    libssl-dev \
    git \
    pkg-config \
    cmake \
    wget \
    openssh-client \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /uvx /bin/

# install python
RUN apt-get update && \
    apt-get install -y curl git cmake gcc g++ libgomp1 libbz2-dev libev-dev libffi-dev libgdbm-dev liblzma-dev libncurses-dev libreadline-dev libsqlite3-dev libssl-dev make tk-dev wget zlib1g-dev
RUN curl -O https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz
RUN tar -xvzf Python-${PYTHON_VERSION}.tgz
RUN cd Python-${PYTHON_VERSION} && \
    ./configure \
        --prefix=/opt/python/${PYTHON_VERSION} \
        --enable-shared \
        --enable-optimizations \
        --enable-ipv6 \
        LDFLAGS=-Wl,-rpath=/opt/python/${PYTHON_VERSION}/lib,--disable-new-dtags && \
    make && make install
# install pip
RUN curl -O https://bootstrap.pypa.io/get-pip.py
RUN /opt/python/${PYTHON_VERSION}/bin/python${PYTHON_MAJOR} get-pip.py
# export PATH
ENV PATH=/opt/python/${PYTHON_VERSION}/bin/:$PATH
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# # install python dependencies
# RUN python3 -m venv /workspace/env
# RUN . /workspace/env/bin/activate && \
#     pip3 install huggingface-hub --no-cache-dir


EXPOSE 8080
ENV RUST_BACKTRACE=1

WORKDIR /app

COPY config-tts.toml .
COPY config-stt.toml .
COPY start_moshi_server_public.sh .

RUN wget https://raw.githubusercontent.com/kyutai-labs/moshi/a40c5612ade3496f4e4aa47273964404ba287168/rust/moshi-server/pyproject.toml
RUN wget https://raw.githubusercontent.com/kyutai-labs/moshi/a40c5612ade3496f4e4aa47273964404ba287168/rust/moshi-server/uv.lock

RUN chmod +x start_moshi_server_public.sh


#ENTRYPOINT ["uv", "run", "--locked", "--project", "./moshi-server", "./start_moshi_server_public.sh"]