#!/bin/bash

## Building llamacpp is required to avoid Illegal instruction errors
## Compiling it in runtime ensures the CPU will contain required instructions

subcommand=$1
shift

case "$subcommand" in
  server_cpu)
    cd /workspace/llama.cpp
    mkdir build
    cd build
    cmake .. -DGGML_RPC=ON -DLLAMA_CURL=OFF
    cmake --build . --config Release -j $(nproc)
    # source /workspace/env/bin/activate
    # # issue with streaming: https://github.com/abetlen/llama-cpp-python/issues/1861
    # CMAKE_ARGS="-DGGML_RPC=on" pip3 install "llama-cpp-python[server]==0.3.7" --force-reinstall --no-cache-dir --ignore-installed
    ;;
  server_nvidia)
    cd /workspace/llama.cpp
    mkdir build
    cd build
    cmake .. -DGGML_RPC=ON -DGGML_CUDA=ON -DGGML_CUDA_ENABLE_UNIFIED_MEMORY=1 -DLLAMA_CURL=OFF
    cmake --build . --config Release -j $(nproc)
    #source /workspace/env/bin/activate
    #CMAKE_ARGS="-DGGML_RPC=on -DGGML_CUDA=on" pip3 install "llama-cpp-python[server]==0.3.7" --force-reinstall --no-cache-dir --ignore-installed
    ;;
  server_amd)
    cd /workspace/llama.cpp
    mkdir build
    HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
      cmake -S . -B build -DLLAMA_CURL=OFF -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release \
      && cmake --build build --config Release -- -j $(nproc)
    ;;
  cpu)
    cd /workspace/llama.cpp
    mkdir build
    cd build
    # GGML_RPC=ON: Builds RPC support
    # BUILD_SHARED_LIBS=OFF: Don't rely on shared libraries like libggml
    # use -DGGML_CUDA=ON for GPU support
    cmake .. -DGGML_RPC=ON -DLLAMA_CURL=OFF
    cmake --build . --config Release -j $(nproc)
    ;;
  nvidia)
    cd /workspace/llama.cpp
    mkdir build
    cd build

    # GGML_RPC=ON: Builds RPC support
    # BUILD_SHARED_LIBS=OFF: Don't rely on shared libraries like libggml
    # use -DGGML_CUDA=ON for GPU support
    cmake .. -DGGML_RPC=ON -DGGML_CUDA=ON -DGGML_CUDA_ENABLE_UNIFIED_MEMORY=1 -DLLAMA_CURL=OFF
    cmake --build . --config Release -j $(nproc)
    ;;
  amd)
    cd /workspace/llama.cpp
    mkdir build
    HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \
      cmake -S . -B build -DLLAMA_CURL=OFF -DGGML_HIP=ON -DGPU_TARGETS=gfx1100 -DCMAKE_BUILD_TYPE=Release \
      && cmake --build build --config Release -- -j $(nproc)
    ;;
  *)
    echo "unknown subcommand: $subcommand"
    exit 1
    ;;
esac