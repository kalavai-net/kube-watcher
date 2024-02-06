import os
from typing import List

from fastapi import FastAPI, HTTPException
from kube_watcher.cost_core import OpenCostAPI

from kube_watcher.models import (
    NodeStatusRequest,
    NodeLabelsRequest,
    NodeCostRequest,
    NamespacesCostRequest,
    DeepsparseDeploymentRequest,
    DeepsparseDeploymentDeleteRequest,
    DeepsparseDeploymentListRequest,
    GenericDeploymentRequest,
    DeleteLabelledResourcesRequest,
    GetLabelledResourcesRequest
)
from kube_watcher.kube_core import (
    KubeAPI
)
from kube_watcher.prometheus_core import PrometheusAPI
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

IN_CLUSTER = "True" == os.getenv("IN_CLUSTER", "True")
PROMETHEUS_ENDPOINT = os.getenv("PROMETHEUS_ENDPOINT", "http://10.43.164.196:9090")
OPENCOST_ENDPOINT = os.getenv("OPENCOST_ENDPOINT", "http://10.43.53.194:9003")

kube_api = KubeAPI(in_cluster=IN_CLUSTER)
app = FastAPI()

@app.get("/v1/get_cluster_capacity")
async def cluster_capacity():
    cluster_capacity = kube_api.extract_cluster_capacity()
    return cluster_capacity

@app.get("/v1/get_cluster_labels")
async def cluster_labels():
    labels = kube_api.extract_cluster_labels()
    return labels

@app.post("/v1/get_node_labels")
async def node_labels(request: NodeLabelsRequest):
    labels = kube_api.get_node_labels(node_names=request.node_names)
    return labels


@app.post("/v1/get_node_stats")
async def node_stats(request: NodeStatusRequest):
    client = PrometheusAPI(url=PROMETHEUS_ENDPOINT, disable_ssl=True) # works as long as we are port forwarding from control plane
    
    return client.get_node_stats(
        node_id=request.node_id,
        start_time=request.start_time,
        end_time=request.end_time,
        chunk_size=request.chunk_size
    )


@app.post("/v1/get_nodes_cost")
async def node_cost(request: NodeCostRequest):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_nodes_computation(
        nodes=request.node_names,
        **request.kubecost_params.model_dump())


@app.post("/v1/get_namespaces_cost")
async def namespace_cost(request: NamespacesCostRequest):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_namespaces_cost(
        namespaces=request.namespace_names,
        **request.kubecost_params.model_dump())


# Create model deployment with deepsparse
@app.post("/v1/deploy_deepsparse_model")
async def namespace_cost(request: DeepsparseDeploymentRequest):
    model_response = kube_api.deploy_deepsparse_model(
        deployment_name=request.deployment_name,
        model_id=request.deepsparse_model_id,
        namespace=request.namespace,
        num_cores=request.num_cores,
        ephemeral_memory=request.ephemeral_memory,
        ram_memory=request.ram_memory,
        task=request.task,
        replicas=request.replicas
    )
    return model_response

@app.post("/v1/delete_deepsparse_model")
async def namespace_cost(request: DeepsparseDeploymentDeleteRequest):
    model_response = kube_api.delete_deepsparse_model(
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )
    return model_response

@app.post("/v1/list_deepsparse_deployments")
async def namespace_cost(request: DeepsparseDeploymentListRequest):
    model_response = kube_api.list_deepsparse_deployments(
        namespace=request.namespace
    )
    return model_response


#### GENERIC_DEPLOYMENT
@app.post("/v1/deploy_generic_model")
async def deploy_ray_model(request: GenericDeploymentRequest):
    return kube_api.deploy_generic_model(request.config) 

@app.post("/v1/delete_labeled_resources")
async def delete_labeled_resources(request: DeleteLabelledResourcesRequest):
    return kube_api.delete_labeled_resources(request.namespace, request.label, request.value)

@app.post("/v1/get_resources_with_label")
async def get_resources_with_label(request: GetLabelledResourcesRequest):
    return kube_api.find_resources_with_label(request.namespace, request.label, request.value)

@app.post("/v1/find_nodeport_url")
async def find_nodeport_url(request: GetLabelledResourcesRequest):
    return kube_api.find_nodeport_url(request.namespace, request.label, request.value)

# Endpoint to check health
@app.get("/v1/health")
async def health():
    return HTTPException(status_code=200, detail="OK")

