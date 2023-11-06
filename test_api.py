import json
import requests
import datetime


URL = "http://localhost:8009"

if __name__ == "__main__":
    
    now_time = datetime.date(2023, 9, 20)
    start = (now_time - datetime.timedelta(days=13)).strftime('%Y-%m-%dT%H:%M:%SZ')
    now = now_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    formatted_window = f"{start},{now}"
    print(formatted_window)
    params = dict(
        node_names=["carlosfm-laptop"],
        kubecost_params={
            "window": formatted_window
        }
    )
    response = requests.get(
        f"{URL}/v1/get_nodes_cost",
        json=params
    )
    print(json.dumps(response.json(), indent=3))
    
    