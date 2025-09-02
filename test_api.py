import json
import requests
import datetime
import time
import yaml

URL = "http://51.159.157.183:30001"
API_KEY = "aad25d2f-b24c-42c2-8a2a-2b2df1ec8bbf"


if __name__ == "__main__":

    # response = requests.get(
    #     f"{URL}/v1/get_job_templates",
    #     headers={"X-API-KEY": "5b3a22a2-6287-4176-b16a-e8fbf7a81ee1", "USER": "carlosfm"},
    #     params={
    #         "type": "model"
    #     }
    # )
    # print(
    #     response.json()
    # )
    # exit()

    with open("templates/sglang/examples/qwen3-0.6b-rocm.yaml", "r") as f:
        values = yaml.safe_load(f)
        values_dict = {variable["name"]: variable['value'] for variable in values}
    with open("templates/sglang/template.yaml", "r") as f:
        template = f.read()
    with open("templates/sglang/values.yaml", "r") as f:
        defaults = f.read()

    response = requests.post(
        f"{URL}/v1/deploy_custom_job",
        headers={"X-API-KEY": API_KEY, "USER": "carlosfm"},
        json={
            "template": template,
            "template_values": values_dict,
            "default_values": defaults,
            "replicas": 1
        }
    )
    print(response.text)
    print(json.dumps(response.json(), indent=3))

    