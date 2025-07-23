import json
import requests
import yaml

URL = "http://51.159.182.127:30001"

if __name__ == "__main__":

    with open("examples/production.yaml", "r") as f:
        values = yaml.safe_load(f)
        values_dict = {variable["name"]: variable['value'] for variable in values}
    with open("template.yaml", "r") as f:
        template = f.read()
    with open("values.yaml", "r") as f:
        defaults = f.read()

    response = requests.post(
        f"{URL}/v1/deploy_custom_job",
        headers={"X-API-KEY": "aad25d2f-b24c-42c2-8a2a-2b2df1ec8bbf", "USER": "carlosfm"},
        json={
            "template": template,
            "template_values": values_dict,
            "default_values": defaults
        }
    )
    print(response.text)
    print(json.dumps(response.json(), indent=3))

    