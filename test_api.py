import json
import requests


URL = "http://localhost:8009"

if __name__ == "__main__":

    params = {
        "node_names": ["carlosfm-laptop"],
    }
    response = requests.get(
        f"{URL}/v1/get_cluster_capacity",
        #json=params
    )
    print(json.dumps(response.json(), indent=3))
    
    