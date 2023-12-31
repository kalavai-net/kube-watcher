import json
import requests
import datetime
import time


URL = "http://10.43.112.76:8000"

if __name__ == "__main__":
    
    response = requests.get(
        f"{URL}/v1/get_cluster_capacity"
    )
    print(response.text)
    exit()
    print(json.dumps(response.json(), indent=3))
    
    exit()
    
    # now_time = datetime.date(2023, 12, 31)
    # start = (now_time - datetime.timedelta(days=13)).strftime('%Y-%m-%dT%H:%M:%SZ')
    # now = now_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    # formatted_window = f"{start},{now}"
    # print(formatted_window)
    # params = dict(
    #     namespace_names=["kube-system"],
    #     kubecost_params={
    #         "window": formatted_window
    #     }
    # )
    # response = requests.get(
    #     f"{URL}/v1/get_namespaces_cost",
    #     json=params
    # )
    # print(json.dumps(response.json(), indent=3))
    
    params = dict(
        deployment_name="mpt-7b",
        namespace="carlosfm",
        deepsparse_model_id="zoo:mpt-7b-dolly_mpt_pretrain-pruned50_quantized",
        ephemeral_memory="42Gi",
        ram_memory="12Gi",
        num_cores=4,
        task="chat"
    )
    response = requests.get(
        f"{URL}/v1/deploy_deepsparse_model",
        json=params
    )
    print(json.dumps(response.json(), indent=3))
    
    time.sleep(15)
    
    params = dict(
        deployment_name="mpt-7b",
        namespace="carlosfm"
    )
    response = requests.get(
        f"{URL}/v1/delete_deepsparse_model",
        json=params
    )
    print(json.dumps(response.json(), indent=3))
    
    
    
    