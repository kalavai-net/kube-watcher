#!/bin/bash

while [ $# -gt 0 ]; do
  case "$1" in
    --command=*)
      command="${1#*=}"
      ;;
    --model_id=*)
      model_id="${1#*=}"
      ;;
    --model_path=*)
      model_path="${1#*=}"
      ;;
    --server_ip=*)
      server_ip="${1#*=}"
      ;;
    --num_nodes=*)
      num_nodes="${1#*=}"
      ;;
    --node_rank=*)
      node_rank="${1#*=}"
      ;;
    --tensor_parallel_size=*)
      tensor_parallel_size="${1#*=}"
      ;;
    --pipeline_parallel_size=*)
      pipeline_parallel_size="${1#*=}"
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

echo ">>>>>>>>>>>>>>>>>>>>>>"
echo "Server IP: $server_ip"
echo "Model ID: $model_id"
echo "Node rank: $node_rank"
echo "Num nodes: $num_nodes"
echo "---->"$extra
echo ">>>>>>>>>>>>>>>>>>>>>>"

HF_HUB_OFFLINE=1

if [ -z "$template_url" ]
then
  template_str=""
else
  wget $template_url -O /home/ray/workspace/template.jinja
  template_str="--chat-template /home/ray/workspace/template.jinja"
fi

if [ "$command" = "server" ]; then
  echo ">> Running as server..."
  python3 -m sglang.launch_server \
    --dist-init-addr $server_ip \
    --nnodes $num_nodes \
    --node-rank $node_rank \
    --model-path $model_path \
    --served-model-name $model_id \
    --host 0.0.0.0 --port 8080 \
    --tp-size $tensor_parallel_size \
    --pp-size $pipeline_parallel_size \
    --tool-call-parser $tool_call_parser \
    $extra \
    $template_str
else
  echo ">> Running as worker..."
  python3 -m sglang.launch_server \
  --dist-init-addr $server_ip \
  --nnodes $num_nodes \
  --node-rank $node_rank \
  --model-path $model_path \
  --served-model-name $model_id \
  --tp-size $tensor_parallel_size \
  --pp-size $pipeline_parallel_size \
  --tool-call-parser $tool_call_parser \
  $extra \
  $template_str
fi

