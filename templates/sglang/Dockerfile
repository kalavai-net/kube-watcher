FROM bundenth/ray:latest AS base

#FROM lmsysorg/sglang:v0.5.2-cu126
FROM lmsysorg/sglang:v0.4.7.post1-cu124

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /home/ray/workspace

# copy over ray scripts
COPY --from=base /home/ray/workspace/ .

RUN apt update && apt install bc wget -y && \
    rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN update-alternatives --set python /usr/bin/python3

# upgrade version
# RUN pip install sglang[all] --no-cache-dir

# COPY common_requirements.txt .
# RUN pip install -r common_requirements.txt --no-cache-dir

COPY run_model.sh .
RUN chmod +x /home/ray/workspace/run_model.sh

