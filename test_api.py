import json
import requests
import datetime
import time


URL = "http://127.0.0.1:8000"

if __name__ == "__main__":

    response = requests.get(
        f"{URL}/v1/get_job_templates",
        headers={"X-API-KEY": "", "USER": "carlosfm", "USER-KEY": "v2x5eEtooZujkJE2lAJtCHZB8bHTQFBXn3sNkI7UfqeHWwa6bv1sjEm1cTkbsMbR9jGlVApPdV1AlC8YWfBY7iMoYwJ5Tof0G8hMQYasucKpZL1ok3z5c5hXB3YbDa2g"},
        # json={
        #     "template": "vllm"
        # }
    )
    print(json.dumps(response.json(), indent=3))

    