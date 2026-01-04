# vLLM template

Deploy LLM models across multiple worker nodes using the vLLM library. This template is designed to work with GPU workers.

## External references

This template makes heavy use of the [vLLM library](https://docs.vllm.ai/en/latest/index.html).

## Key template variables

- `workers`: Number of workers per deployment (for tensor and pipeline parallelism, i.e. how many pieces to divide the model into)
- `model_id`: Huggingface repository to load from [Huggingface](https://huggingface.co/models). This usually takes the form of `OrgName/ModelID`
- `working_memory`: Temporary disk space where model weights are placed for loading. Needs to be big enough to hold the entire model weights in a single worker node.
- `hf_token` (optional): Huggingface token, required to load licensed model weights
- `extra` (optional): any [extra parameters](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html#cli-reference) to pass to vLLM engine. Expected format: `--parameter1_name parameter1_value --parameterX_name parameterX_value`
- `tensor_parallel_size`: Tensor parallelism (use the number of GPUs per node)
- `pipeline_parallel_size`: Pipeline parallelism (use the number of nodes)

If you have a [LiteLLM server](https://github.com/kalavai-net/kalavai-client/tree/main/templates/litellm) deployed in your pool (default for [public LLM pool](https://kalavai-net.github.io/kalavai-client/public_llm_pool/)), you can pass on the following parameters to rregister the model with it:

- `litellm_key` as the API key.
- `litellm_base_url` as the endpoint for the LiteLLM job.


## How to use

Get default values, edit them and deploy:
```bash
kalavai job defaults vllm > values.yaml
# edit values.yaml as required
kalavai job run vllm --values values.yaml
```

Find out the url endpoint of the model with:

```bash
$ kalavai job list 

┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Deployment        ┃ Status                            ┃ Endpoint               ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ vllm-deployment-1 │ Available: All replicas are ready │ http://100.8.0.2:31992 │
└───────────────────┴───────────────────────────────────┴────────────────────────┘
```

This is a model endpoint that can be interacted as you would any [LLM server](https://docs.vllm.ai/en/latest/getting_started/quickstart.html#using-openai-completions-api-with-vllm). For example:
```bash
curl http://100.10.0.2:31992/v1/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "prompt": "San Francisco is a",
        "max_tokens": 100,
        "temperature": 0
    }'
```

Also from python:
```python
from openai import OpenAI

# Modify OpenAI's API key and API base to use vLLM's API server.
openai_api_key = "EMPTY"
openai_api_base = "http://100.8.0.2:31992/v1"
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)
completion = client.completions.create(model="facebook/opt-350m",
                                      prompt="San Francisco is a")
print("Completion result:", completion)
```

## Examples

Check out the [qwen example](examples/qwen2.5-0.5B.yaml),ready for deployment.


## ROCm

Install cupy?


RAY start on nodes:

export HF_HOME=/app/models 
ray start --node-ip-address=69.57.212.209 --head
ray start --address=69.57.212.209:6379 --node-ip-address=69.57.212.210
ray start --address=69.57.212.209:6379 --node-ip-address=69.57.212.221

--> From pre-built

sudo docker run -it --rm \
    --network=host \
    --privileged \
    --device /dev/kfd \
    --device /dev/dri \
    --shm-size=9gb \
    rocm/vllm:rocm6.4.1_vllm_0.10.1_20250909

vllm serve Qwen/Qwen2.5-0.5B \
  --host 0.0.0.0 --port 8080 --distributed-executor-backend="ray" --max-model-len 5000 --cpu-offload-gb 64 --pipeline-parallel-size=3 


*******************************

---> From instructions https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html?device=rocm#build-an-image-with-vllm

vllm serve Qwen/Qwen2.5-0.5B \
  --host 0.0.0.0 --port 8080 --tensor-parallel-size 1 --distributed-executor-backend ray --enforce-eager
  

curl http://localhost:8080/v1/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "Qwen/Qwen2.5-0.5B",
        "prompt": "San Francisco is a",
        "max_tokens": 100,
        "temperature": 0
    }'

curl "http://localhost:8080/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "Qwen/Qwen2.5-0.5B",
        "messages": [
            {
                "role": "developer",
                "content": "Talk like a pirate."
            },
            {
                "role": "user",
                "content": "Are semicolons optional in JavaScript?"
            }
        ]
    }'


curl "http://51.159.144.100:30768/v1/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer sk-25021984" \
    -d '{                     
        "model": "qwen2.5-3B",
        "prompt": "Once upon a time",
        "max_tokens": 50,
        "temperature": 0.7
    }'






## MS AMD nodes

Install docker

```bash
# Install required packages
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the Docker repository with the correct Ubuntu code name
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  jammy stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update the package index
sudo apt-get update

# Install Docker
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Install ROCm & AMD drivers:


```bash
wget https://repo.radeon.com/amdgpu-install/6.4.4/ubuntu/noble/amdgpu-install_6.4.60404-1_all.deb
sudo apt install ./amdgpu-install_6.4.60404-1_all.deb
sudo apt update
sudo apt install python3-setuptools python3-wheel
sudo usermod -a -G render,video $LOGNAME # Add the current user to the render and video groups
sudo apt install rocm
sudo apt install "linux-headers-$(uname -r)"
sudo apt install amdgpu-dkms
```

Test:

docker run -it --rm \
    --network=host \
    --privileged \
    --device /dev/kfd \
    --device /dev/dri \
    --shm-size=11gb \
    -v ./models:/app/models \
    rocm/vllm:rocm6.4.1_vllm_0.10.1_20250909

vllm serve Qwen/Qwen2.5-0.5B --distributed-executor-backend="ray"