import json
import requests
import datetime
import time
import yaml

URL = "http://0.0.0.0:8000"

if __name__ == "__main__":

    response = requests.get(
        f"{URL}/v1/get_job_templates",
        headers={"X-API-KEY": "14429b75-b1e4-4987-8bcf-afa00c69644b", "USER": "carlosfm"},
        params={
            "type": "model"
        }
    )
    print(
        response.json()
    )
    exit()

    with open("templates/unmute/values.yaml", "r") as f:
        values = yaml.safe_load(f)
        values_dict = {variable["name"]: variable['value'] for variable in values}
    with open("templates/unmute/template.yaml", "r") as f:
        template = f.read()
    with open("templates/unmute/values.yaml", "r") as f:
        defaults = f.read()

    response = requests.post(
        f"{URL}/v1/deploy_custom_job",
        headers={"X-API-KEY": "14429b75-b1e4-4987-8bcf-afa00c69644b", "USER": "carlosfm"},
        json={
            "template": template,
            "template_values": values_dict,
            "default_values": defaults
        }
    )
    print(response.text)
    print(json.dumps(response.json(), indent=3))

    