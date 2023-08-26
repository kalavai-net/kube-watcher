import os

from kubernetes import client
from fastapi import FastAPI

from app.models import (
    NodeStatusRequest,
    ValidateUserRequest,
    LinNodeUserRequest
)
from app.kube_core import (
    load_config,
    extract_cluster_capacity
)
from app.prometheus_core import PrometheusAPI
from app.anvil_core import (
    validate_anvil_user,
    link_user_node
)


IN_CLUSTER = "True" == os.getenv("IN_CLUSTER", "True")
PROMETHEUS_ENDPOINT = os.getenv("PROMETHEUS_ENDPOINT", "http://159.65.30.72:9090")
ANVIL_CLIENT_KEY = os.getenv("ANVIL_CLIENT_KEY", "client_RIH6JESGB46H5H2C26QNTEPN-WCK6VK5MLEHD7BEC")

load_config(in_cluster=IN_CLUSTER)
v1 = client.CoreV1Api()
app = FastAPI()


@app.get("/v1/get_capacity")
async def capacity():
    nodes = v1.list_node()
    capacity = extract_cluster_capacity(nodes.items)
    return capacity


@app.get("/v1/get_node_stats")
async def node_stats(request: NodeStatusRequest):
    client = PrometheusAPI(url=PROMETHEUS_ENDPOINT, disable_ssl=True) # works as long as we are port forwarding from control plane
    
    return client.get_node_stats(
        node_id=request.node_id,
        start_time=request.start_time,
        end_time=request.end_time,
        chunk_size=request.chunk_size
    )


@app.get("/v1/validate_user")
async def validate_user(request: ValidateUserRequest):
    return validate_anvil_user(
        anvil_key=ANVIL_CLIENT_KEY,
        username=request.username,
        password=request.password
    )

@app.get("/v1/link_user_node")
async def post_user_node(request: LinNodeUserRequest):
    return link_user_node(
        anvil_key=ANVIL_CLIENT_KEY,
        username=request.user.username,
        password=request.user.password,
        node_name=request.node_name
    )