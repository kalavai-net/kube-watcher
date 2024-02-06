import httpx
from typing import Any, Dict, List
from kube_watcher.models import (
    NodeStatusRequest,
    NodeLabelsRequest,
    NodeCostRequest,
    NamespacesCostRequest,
    DeepsparseDeploymentRequest,
    DeepsparseDeploymentDeleteRequest,
    DeepsparseDeploymentListRequest,
    GenericDeploymentRequest,
    DeleteLabelledResourcesRequest
)

class KubeWatcherClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        if self.api_key:
            self.headers = {"Authorization": f"Bearer {api_key}"}
        else:
            self.headers = {}

        self.client = httpx.Client()

    def get_cluster_capacity(self) -> Any:
        url = f"{self.base_url}/v1/get_cluster_capacity"
        response = self.client.get(url, headers=self.headers)
        return response.json()

    def get_cluster_labels(self) -> Any:
        url = f"{self.base_url}/v1/get_cluster_labels"
        response = self.client.get(url, headers=self.headers)
        return response.json()

    def get_node_labels(self, node_labels_request: NodeLabelsRequest) -> Any:
        url = f"{self.base_url}/v1/get_node_labels"
        if type(node_labels_request) != dict:
            node_labels_request = node_labels_request.model_dump()

        response = self.client.post(url, json=node_labels_request, headers=self.headers)
        return response.json()

    def get_node_stats(self, node_status_request: NodeStatusRequest) -> Any:
        url = f"{self.base_url}/v1/get_node_stats"
        if type(node_status_request) != dict:
            node_status_request = node_status_request.model_dump()
        response = self.client.post(url, json=node_status_request, headers=self.headers)
        return response.json()

    def get_nodes_cost(self, node_cost_request: NodeCostRequest) -> Any:
        url = f"{self.base_url}/v1/get_nodes_cost"
        if type(node_cost_request) != dict:
            node_cost_request = node_cost_request.model_dump()
        response = self.client.post(url, json=node_cost_request, headers=self.headers)
        return response.json()

    def get_namespaces_cost(self, namespaces_cost_request: NamespacesCostRequest) -> Any:
        url = f"{self.base_url}/v1/get_namespaces_cost"
        if type(namespaces_cost_request) != dict:
            namespaces_cost_request = namespaces_cost_request.model_dump()
        response = self.client.post(url, json=namespaces_cost_request, headers=self.headers)
        return response.json()

    def deploy_deepsparse_model(self, deepsparse_deployment_request: DeepsparseDeploymentRequest) -> Any:
        url = f"{self.base_url}/v1/deploy_deepsparse_model"
        if type(deepsparse_deployment_request) != dict:
            deepsparse_deployment_request = deepsparse_deployment_request.model_dump()
        response = self.client.post(url, json=deepsparse_deployment_request, headers=self.headers)
        return response.json()

    def delete_deepsparse_model(self, deepsparse_deployment_delete_request: DeepsparseDeploymentDeleteRequest) -> Any:
        url = f"{self.base_url}/v1/delete_deepsparse_model"
        if type(deepsparse_deployment_delete_request) != dict:
            deepsparse_deployment_delete_request = deepsparse_deployment_delete_request.model_dump()
        response = self.client.post(url, json=deepsparse_deployment_delete_request, headers=self.headers)
        return response.json()

    def list_deepsparse_deployments(self, deepsparse_deployment_list_request: DeepsparseDeploymentListRequest) -> Any:
        url = f"{self.base_url}/v1/list_deepsparse_deployments"
        if type(deepsparse_deployment_list_request) != dict:
            deepsparse_deployment_list_request = deepsparse_deployment_list_request.model_dump()
        response = self.client.post(url, json=deepsparse_deployment_list_request, headers=self.headers)
        return response.json()

    def deploy_generic_model(self, generic_deployment_request: GenericDeploymentRequest) -> Any:
        url = f"{self.base_url}/v1/deploy_generic_model"
        if type(generic_deployment_request) != dict:
            generic_deployment_request = generic_deployment_request.model_dump()
        response = self.client.post(url, json=generic_deployment_request, headers=self.headers)
        return response.json()

    def delete_labeled_resources(self, delete_labelled_resources_request: DeleteLabelledResourcesRequest) -> Any:
        url = f"{self.base_url}/v1/delete_labeled_resources"
        if type(delete_labelled_resources_request) != dict:
            delete_labelled_resources_request = delete_labelled_resources_request.model_dump()

        response = self.client.post(url, json=delete_labelled_resources_request, headers=self.headers)
        return response.json()

    def get_resources_with_label(self, namespace:str, label_key:str, label_value=None) -> Any:
        url = f"{self.base_url}/v1/get_resources_with_label"
        response = self.client.post(url, json={"namespace":namespace, "label":label_key, "value":label_value}, headers=self.headers)
        return response.json()
    
#@app.post("/v1/find_nodeport_url")
#async def find_nodeport_url(request: GetLabelledResourcesRequest):
#    return kube_api.find_nodeport_url(request.namespace, request.label, request.value)

    def find_nodeport_url(self, namespace:str, label_key:str, label_value=None) -> Any:
        url = f"{self.base_url}/v1/find_nodeport_url"
        response = self.client.post(url, json={"namespace":namespace, "label":label_key, "value":label_value}, headers=self.headers)
        return response.json()
    
    def close(self):
        self.client.close()

    def __del__(self):
        self.close()

    def health(self) -> bool:
        url = f"{self.base_url}/v1/health"

        try:
            response = self.client.get(url, headers=self.headers)
        except Exception as e:
            return False
        return response.status_code == 200