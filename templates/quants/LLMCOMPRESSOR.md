# LLM Compressor for vLLM

https://docs.vllm.ai/projects/llm-compressor/en/latest/steps/choosing-model/

- Models from Hugging Face
- Compression scheme: W8A8-FP8 (+8.9 compute capability)
    * https://docs.vllm.ai/projects/llm-compressor/en/latest/guides/compression_schemes/
- Compression algorithm: AWQ/GPTQ best (but expensive to run), RTN fast (moderate quality)
- Dataset required for AWQ/GPTQ: popular ones --> https://docs.vllm.ai/projects/llm-compressor/en/latest/steps/choosing-dataset/#key-considerations
    * generally 128-512 samples are enough


## Example

https://docs.vllm.ai/projects/llm-compressor/en/latest/steps/compress/

pip install llmcompressor
python llm_compressor_test.py