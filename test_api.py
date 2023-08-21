import requests


URL = "http://159.65.30.72:31230"

if __name__ == "__main__":

    params = {
        "node_id": "carlosfm-laptop"
    }
    response = requests.get(
        f"{URL}/v1/get_node_stats",
        json=params
    )
    print(response.json())