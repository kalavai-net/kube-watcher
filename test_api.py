import json
import requests
import datetime
import time
import yaml

URL = "http://0.0.0.0:8000"

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

    with open("templates/llamacpp/examples/qwen.yaml", "r") as f:
        values = yaml.safe_load(f)
        values_dict = {variable["name"]: variable['value'] for variable in values}
    with open("templates/llamacpp/template.yaml", "r") as f:
        template = f.read()
    with open("templates/llamacpp/values.yaml", "r") as f:
        defaults = f.read()

    response = requests.post(
        f"{URL}/v1/deploy_custom_job",
        headers={"X-API-KEY": "7f027dfd-5177-4b76-9d1c-06115f12b5b6", "USER": "carlosfm"},
        json={
            "template": template,
            "template_values": values_dict,
            "default_values": defaults,
            "replicas": 2
        }
    )
    print(response.text)
    print(json.dumps(response.json(), indent=3))

    