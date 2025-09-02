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
      hf download \
        $repo_id \
        $element \
        --local-dir $local_dir >/dev/null 2>&1
    done

    if [[ "${#elements[@]}" -gt 1 ]]; then
      # choose the first file
      mapfile -t sorted_elements < <(printf "%s\n" "${elements[@]}" | sort)
      echo "${sorted_elements[0]}"
    else
      echo $input_string
    fi
}


#################
# download model #
#################
echo "Downloading: "$model_filename
model=$(download $model_filename)
echo "-----> This is the model: "$model


##################
# run API server #
##################
if [ -z $rpc_servers ]; then
  workers=""
else
  workers="--rpc "$rpc_servers
  echo "Connecting to workers: "$workers
fi

/workspace/llama.cpp/build/bin/llama-server \
  -m $local_dir/$model \
  --alias $model \
  --host 0.0.0.0 \
  --port 8080 \
  $workers \
  $extra
