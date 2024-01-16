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
    DeepsparseDeploymentDeleteRequest,
    DeepsparseDeploymentListRequest,
    RayDeploymentRequest,
    RayDeploymentDeleteRequest,
    RayDeploymentListRequest,
    GenericDeploymentRequest,
)
from app.kube_core import KubeAPI
from app.prometheus_core import PrometheusAPI


IN_CLUSTER = "True" == os.getenv("IN_CLUSTER", "True")
PROMETHEUS_ENDPOINT = os.getenv("PROMETHEUS_ENDPOINT", "http://10.43.164.196:9090")
OPENCOST_ENDPOINT = os.getenv("OPENCOST_ENDPOINT", "http://10.43.53.194:9003")

kube_api = KubeAPI(in_cluster=IN_CLUSTER)
app = FastAPI()


@app.post("/v1/get_cluster_capacity")
async def cluster_capacity():
    cluster_capacity = kube_api.extract_cluster_capacity()
    return cluster_capacity


@app.post("/v1/get_cluster_labels")
async def cluster_labels():
    labels = kube_api.extract_cluster_labels()
    return labels


@app.post("/v1/get_node_labels")
async def node_labels(request: NodeLabelsRequest):
    labels = kube_api.get_node_labels(node_names=request.node_names)
    return labels


@app.post("/v1/get_node_stats")
async def node_stats(request: NodeStatusRequest):
    client = PrometheusAPI(
        url=PROMETHEUS_ENDPOINT, disable_ssl=True
    )  # works as long as we are port forwarding from control plane

    return client.get_node_stats(
        node_id=request.node_id,
        start_time=request.start_time,
        end_time=request.end_time,
        chunk_size=request.chunk_size,
    )


@app.post("/v1/get_nodes_cost")
async def node_cost(request: NodeCostRequest):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_nodes_computation(
        nodes=request.node_names, **request.kubecost_params.model_dump()
    )


@app.post("/v1/get_namespaces_cost")
async def namespace_cost(request: NamespacesCostRequest):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_namespaces_cost(
        namespaces=request.namespace_names, **request.kubecost_params.model_dump()
    )


# Create model deployment with deepsparse
@app.post("/v1/deploy_deepsparse_model")
async def deploy_deepsparse_model(request: DeepsparseDeploymentRequest):
    model_response = kube_api.deploy_deepsparse_model(
        deployment_name=request.deployment_name,
        model_id=request.deepsparse_model_id,
        namespace=request.namespace,
        num_cores=request.num_cores,
        ephemeral_memory=request.ephemeral_memory,
        ram_memory=request.ram_memory,
        task=request.task,
        replicas=request.replicas,
    )
    return model_response


@app.post("/v1/delete_deepsparse_model")
async def delete_deepsparse_model(request: DeepsparseDeploymentDeleteRequest):
    model_response = kube_api.delete_deepsparse_model(
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )
    return model_response


@app.post("/v1/list_deepsparse_deployments")
async def list_deepsparse_deployments(request: DeepsparseDeploymentListRequest):
    model_response = kube_api.list_deepsparse_deployments(namespace=request.namespace)
    return model_response


#### RAY
# Ray with CRD needs a different approach to deployment
# This could be generalised to all CRDs!?


# Create model deployment with deepsparse
@app.post("/v1/deploy_ray_model")
async def deploy_ray_model(request: RayDeploymentRequest):
    model_response = kube_api.deploy_ray_model(
        namespace=request.namespace,
        deployment_name=request.deployment_name,
        model_id=request.ray_model_id,
        num_cpus=request.num_cpus,
        num_gpus=request.num_gpus,
        num_replicas=request.num_replicas,
        tokenizer_args=request.tokenizer_args,
        tokenizing_args=request.tokenizing_args,
        generation_args=request.generation_args,
        model_args=request.ray_model_args,
    )
    return model_response


@app.post("/v1/delete_ray_model")
async def delete_ray_model(request: RayDeploymentDeleteRequest):
    model_response = kube_api.delete_ray_model(
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )
    return model_response


@app.post("/v1/list_ray_deployments")
async def list_ray_deployments(request: RayDeploymentListRequest):
    model_response = kube_api.list_ray_deployments(namespace=request.namespace)
    return model_response


#### GENERIC_DEPLOYMENT
# Deploy a model from a config
@app.post("/v1/deploy_generic_model")
async def deploy_ray_model(request: GenericDeploymentRequest):
    if request.crd:
        model_response = kube_api.deploy_ray_model(request.config)
    else:
        model_response = kube_api.deploy_generic_model(request.config)

    return model_response
