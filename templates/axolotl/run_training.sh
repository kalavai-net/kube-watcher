#!/bin/bash

cache_dir="/home/ray/cache"

while [ $# -gt 0 ]; do
  case "$1" in
    --cache_dir=*)
      cache_dir="${1#*=}"
      ;;
    *)
      printf "***************************\n"
      printf "* Error: Invalid argument.*\n"
      printf "***************************\n"
      exit 1
  esac
  shift
done

source /home/ray/workspace/env/bin/activate

axolotl train axolotl_config.yaml
GRADIO_SERVER_PORT=8000 axolotl inference axolotl_config.yaml --lora-model-dir="./outputs/lora-out"
