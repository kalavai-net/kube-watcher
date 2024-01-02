import os
from typing import List

from fastapi import FastAPI
from app.cost_core import OpenCostAPI

from app.models import (
    NodeStatusRequest,
    NodeLabelsRequest,
    NodeCostRequest,
    NamespacesCostRequest,
    DeepsparseDeploymentRequest,
    DeepsparseDeploymentDeleteRequest
)
from app.kube_core import (
    KubeAPI
)
from app.prometheus_core import PrometheusAPI


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

@app.get("/v1/get_node_labels")
async def node_labels(request: NodeLabelsRequest):
    labels = kube_api.get_node_labels(node_names=request.node_names)
    return labels


@app.get("/v1/get_node_stats")
async def node_stats(request: NodeStatusRequest):
    client = PrometheusAPI(url=PROMETHEUS_ENDPOINT, disable_ssl=True) # works as long as we are port forwarding from control plane
    
    return client.get_node_stats(
        node_id=request.node_id,
        start_time=request.start_time,
        end_time=request.end_time,
        chunk_size=request.chunk_size
    )


@app.get("/v1/get_nodes_cost")
async def node_cost(request: NodeCostRequest):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_nodes_computation(
        nodes=request.node_names,
        **request.kubecost_params.model_dump())


@app.get("/v1/get_namespaces_cost")
async def namespace_cost(request: NamespacesCostRequest):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_namespaces_cost(
        namespaces=request.namespace_names,
        **request.kubecost_params.model_dump())


# Create model deployment with deepsparse
@app.get("/v1/deploy_deepsparse_model")
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

@app.get("/v1/delete_deepsparse_model")
async def namespace_cost(request: DeepsparseDeploymentDeleteRequest):
    model_response = kube_api.delete_deepsparse_model(
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )
    return model_response
