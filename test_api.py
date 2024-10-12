import json
import requests
import datetime
import time


URL = "http://127.0.0.1:8000"

if __name__ == "__main__":
    
    
    response = requests.get(
        f"{URL}/v1/get_nodes",
        headers={"X-API-KEY": "r"}
    )
    print(json.dumps(response.json(), indent=3))
    