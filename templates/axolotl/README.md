# axolotl API

Fine tune LoRA and QLoRA with small datasets

Axolotl seems to handle multiple GPU easier, and yaml configs to train: https://docs.axolotl.ai/docs/ray-integration.html


## Examples

https://github.com/axolotl-ai-cloud/axolotl/tree/main/examples

### Custom training

axolotl train examples/axolotl_config.yaml

Then inference with:

axolotl inference my_training.yml --lora-model-dir="./outputs/lora-out" --gradio

