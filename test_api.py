import json
import requests
import datetime
import yaml

URL = "http://51.159.177.196:30001" # "https://kube.cogenai.kalavai.net"
API_KEY = ""
PRIORITY_CLASS = "test-low-priority"
USER_SPACE = "shadow"


if __name__ == "__main__":

    # response = requests.post(
    #     f"{URL}/v1/fetch_compute_usage",
    #     headers={"X-API-KEY": API_KEY},
    #     json={
    #         "node_labels": {
    #             "kalavai.cluster.user": "shadow",
                
    #         },
    #         "start_time": "2026-03-19T00:00:00",
    #         "end_time": "now",
    #     }
    # )
    # result = response.json()
    # print(
    #     json.dumps(result, indent=2)
    # )
    # exit()

    target_labels = {
        "kalavai/instance": "rtx-a4500"
    }
    with open("templates/diffusers/examples/flux-shadow.yaml", "r") as f:
        values = yaml.safe_load(f)
        values_dict = {variable["name"]: variable['value'] for variable in values}
    with open("templates/diffusers/template.yaml", "r") as f:
        template = f.read()
    with open("templates/diffusers/values.yaml", "r") as f:
        defaults = f.read()

    response = requests.post(
        f"{URL}/v1/deploy_custom_job",
        headers={"X-API-KEY": API_KEY, "USER": "carlosfm"},
        json={
            "template": template,
            "force_namespace": USER_SPACE,
            "template_values": values_dict,
            "default_values": defaults,
            "target_labels": target_labels,
            "random_suffix": False,
            "replicas": 1,
            "priority": PRIORITY_CLASS
        }
    )
    result = response.json()
    print(
        json.dumps(result, indent=2)
    )

    