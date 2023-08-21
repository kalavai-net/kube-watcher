import os

from kubernetes import client
from fastapi import FastAPI

from app.models import NodeStatusRequest
from app.kube_core import (
    load_config,
    extract_cluster_capacity
)
from app.prometheus_core import PrometheusAPI

IN_CLUSTER = "True" == os.getenv("IN_CLUSTER", "True")
PROMETHEUS_ENDPOINT = os.getenv("PROMETHEUS_ENDPOINT", "http://159.65.30.72:9090")

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

