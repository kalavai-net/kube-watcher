# SGlang template

Info on distributed deployment: https://docs.skypilot.co/en/latest/examples/models/deepseek-r1.html


## ROCm

DOCKER_BUILDKIT=1 docker build --build-arg BASE_IMAGE="rocm/vllm-dev:navi_base" -f Dockerfile_rocm_gfx1100 -t bundenth/test-sglang-rocm:latest .
docker push bundenth/test-sglang-rocm
docker run -it --rm \
    --ipc=host \
    --privileged \
    --shm-size 16g \
    --device=/dev/kfd \
    --device=/dev/dri \
    --group-add video \
    --cap-add=SYS_PTRACE \
    --cap-add=CAP_SYS_ADMIN \
    --security-opt seccomp=unconfined \
    --security-opt apparmor=unconfined \
    --env "HIP_VISIBLE_DEVICES=0" \
    -p 3000:3000 \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    --name sglang_server "lmsysorg/sglang:v0.4.5.post2-rocm630" 

python -m sglang.launch_server \
  --nnodes 1 \
  --node-rank 0 \
  --model-path Qwen/Qwen2.5-0.5B \
  --host 0.0.0.0 --port 8080

