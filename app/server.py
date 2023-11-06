import os
from typing import List

from fastapi import FastAPI
from app.cost_core import OpenCostAPI

from app.models import (
    NodeStatusRequest,
    ValidateUserRequest,
    NodeLabelsRequest,
    LinkNodeUserRequest,
    NodeCostRequest,
    NamespacesCostRequest,
    RayClusterRequest
)
from app.kube_core import (
    KubeAPI
)
from app.prometheus_core import PrometheusAPI
from app.anvil_core import (
    validate_anvil_user,
    link_user_node
)


IN_CLUSTER = "True" == os.getenv("IN_CLUSTER", "True")
PROMETHEUS_ENDPOINT = os.getenv("PROMETHEUS_ENDPOINT", "http://159.65.30.72:9090")
OPENCOST_ENDPOINT = os.getenv("OPENCOST_ENDPOINT", "http://10.152.183.80:9003")
ANVIL_CLIENT_KEY = os.getenv("ANVIL_CLIENT_KEY", "client_RIH6JESGB46H5H2C26QNTEPN-WCK6VK5MLEHD7BEC")

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


@app.get("/v1/validate_user")
async def validate_user(request: ValidateUserRequest):
    return validate_anvil_user(
        anvil_key=ANVIL_CLIENT_KEY,
        username=request.username,
        password=request.password
    )

@app.get("/v1/link_user_node")
async def post_user_node(request: LinkNodeUserRequest):
    return link_user_node(
        anvil_key=ANVIL_CLIENT_KEY,
        username=request.user.username,
        password=request.user.password,
        node_name=request.node_name,
        os=request.os
    )

@app.get("/v1/create_ray_cluster")
async def create_ray_cluster(request: RayClusterRequest):
    result = kube_api.create_ray_cluster(
        namespace=request.namespace,
        cluster_config="data/ray_cluster.yaml",
        nodeport_config="data/ray_ndoeport.yaml"
    )
    return result