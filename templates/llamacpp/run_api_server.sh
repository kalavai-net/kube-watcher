#!/bin/bash

local_dir=/tmp
port=8080
extra=""

while [ $# -gt 0 ]; do
  case "$1" in
    --repo_id=*)
      repo_id="${1#*=}"
      ;;
    --model_filename=*)
      model_filename="${1#*=}"
      ;;
    --local_dir=*)
      local_dir="${1#*=}"
      ;;
    --rpc_servers=*)
      rpc_servers="${1#*=}"
      ;;
    --port=*)
      port="${1#*=}"
      ;;
    --extra=*)
      extra="${1#*=}"
      ;;
    *)
      printf "***************************\n"
      printf "* Error: Invalid argument.*\n"
      printf "***************************\n"
      exit 1
  esac
  shift
done

download() {
    local input_string="$1"
    IFS=',' read -ra elements <<< "$input_string"
    
    for element in "${elements[@]}"; do
      huggingface-cli download \
        $repo_id \
        $element \
        --local-dir $local_dir \
        --local-dir-use-symlinks False
    done

    if [[ "${#elements[@]}" -gt 1 ]]; then
      # choose the first file
      mapfile -t sorted_elements < <(printf "%s\n" "${elements[@]}" | sort)
      echo "${sorted_elements[0]}"
    else
      echo $input_string
    fi
}

source /workspace/env/bin/activate

#################
# download model #
#################
# alternatively, load with server python3 -m llama_cpp.server --hf_model_repo_id Qwen/Qwen2-0.5B-Instruct-GGUF --model '*q8_0.gguf'
echo "Downloading: "$model_filename
model=$(download $model_filename)
echo "-----> This is the model: "$model

## Create config ##
# python /workspace/generate_config.py \
#   --port $port --host 0.0.0.0 \
#   --local_dir $local_dir \
#   --model $model \
#   --output-filename /workspace/config.json

##################
# run API server #
##################
if [ -z $rpc_servers ]; then
  workers=""
else
  workers="--rpc "$rpc_servers
  echo "Connecting to workers: "$workers
fi

# python -m llama_cpp.server \
#   --config_file /workspace/config.json \
#   $workers \
#   $extra

/workspace/llama.cpp/build/bin/llama-server \
  -m $local_dir/$model \
  --alias $model \
  --host 0.0.0.0 \
  --port 8080 \
  $workers