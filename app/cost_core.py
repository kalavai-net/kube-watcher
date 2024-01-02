"""
Monitor kubernetes computation cost via opencost

kubectl port-forward --namespace opencost service/opencost 9003 9090

Send HTTP requests to 9003

Documentation: https://www.opencost.io/docs/integrations/api

Full API: https://github.com/opencost/opencost/blob/develop/docs/swagger.json
"""
import os
import json
import requests
from urllib.parse import urljoin


class OpenCostAPI():
    def __init__(self, base_url):
        self.base_url = base_url
    
    def _form_url(self, endpoint):
        return urljoin(self.base_url, endpoint)
    
    def get_nodes_computation(self, nodes: list=None, **kwargs):
        # https://docs.kubecost.com/apis/apis-overview/allocation
        kwargs["aggregate"] = "node"
        result = requests.get(
            self._form_url(endpoint="/allocation/compute"),
            params=kwargs
        )
        data = result.json()['data']
        if nodes is None:
            return data
        else:
            return {name: info for block in data for name, info in block.items() if name in nodes}


    def get_namespaces_cost(self, namespaces: list=None, **kwargs):
        # https://docs.kubecost.com/apis/apis-overview/allocation
        kwargs["aggregate"] = "namespace"
        result = requests.get(
            self._form_url(endpoint="/allocation/compute"),
            params=kwargs
        )
        data = result.json()['data']
        if namespaces is None:
            return data
        else:
            return {name: info for block in data for name, info in block.items() if name in namespaces}


if __name__ == "__main__":
    
    BASE_URL = os.getenv("OPENCOST_URL", default="http://10.43.53.194:9003")
    opencost = OpenCostAPI(base_url=BASE_URL)

    result = opencost.get_namespaces_cost(
        #window="2023-09-15T20:16:00Z,2023-09-21T21:16:00Z",
        window="today",
        accumulate=True,
        #resolution="1s",
        namespaces=["kube-system"])
    print(json.dumps(result, indent=3))
    