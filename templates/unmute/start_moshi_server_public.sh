#!/bin/bash
# This is the public-facing version.
set -ex

export LD_LIBRARY_PATH=$(python3 -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')

uvx --from 'huggingface_hub[cli]' huggingface-cli login --token $HUGGING_FACE_HUB_TOKEN

CARGO_TARGET_DIR=/app/target cargo install --features cuda moshi-server@0.6.3

/root/.cargo/bin/moshi-server $@