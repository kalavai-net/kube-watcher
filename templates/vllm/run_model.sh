#!/bin/bash

cache_dir="/cache"
tool_call_parser="llama3_json"
template_url=""
tensor_parallel_size=1
pipeline_parallel_size=1
model_name=""


while [ $# -gt 0 ]; do
  case "$1" in
    --model_path=*)
      model_path="${1#*=}"
      ;;
    --model_id=*)
      model_id="${1#*=}"
      ;;
    --model_name=*)
      model_name="${1#*=}"
      ;;
    --tensor_parallel_size=*)
      tensor_parallel_size="${1#*=}"
      ;;
    --pipeline_parallel_size=*)
      pipeline_parallel_size="${1#*=}"
      ;;
    --lora_modules=*)
      lora_modules="${1#*=}"
      ;;
    --extra=*)
      extra="${1#*=}"
      ;;
    --template_url=*)
      template_url="${1#*=}"
      ;;
    --tool_call_parser=*)
      tool_call_parser="${1#*=}"
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

if [ -z "$lora_modules" ]
then
  lora=""
else
  # download each lora adaptor, then create lora modules string
  IFS=';' read -r -a loras <<< "$lora_modules" # split into array
  all_loras=()
  for lora in "${loras[@]}"
  do
      if [ -z $lora ]; then
        continue
      fi
      # download
      dir=$cache_dir"/"$lora
      huggingface-cli download \
        $lora \
        --local-dir $dir \
        --local-dir-use-symlinks False

      # convert to lora string https://docs.vllm.ai/en/v0.5.5/models/lora.html#serving-lora-adapters
      safe_lora=`echo $lora | tr /- _`
      all_loras+=("${safe_lora}=${dir}")

      function join_by {
        local d=${1-} f=${2-}
        if shift 2; then
          printf %s "$f" "${@/#/$d}"
        fi
      }
  done
  lora="--enable-lora --lora-modules "$(join_by " " "${all_loras[@]}")
fi

if [ -z "$template_url" ]
then
  template_str=""
else
  wget $template_url -O /home/ray/workspace/template.jinja
  template_str="--chat-template /home/ray/workspace/template.jinja"
fi

if [ -z "$model_name" ]
then
  name=$model_id
else
  name=$model_name
fi

HF_HUB_OFFLINE=1
echo "----> [extra params] "$extra
#python -m vllm.entrypoints.openai.api_server \
#  --model $model_path \
vllm serve $model_id \
  --served-model-name $name \
  --host 0.0.0.0 --port 8080 \
  --tensor-parallel-size $tensor_parallel_size \
  --pipeline-parallel-size $pipeline_parallel_size \
  --enable-auto-tool-choice \
  --tool-call-parser $tool_call_parser \
  --distributed-executor-backend="ray" \
  $lora \
  $extra \
  $template_str