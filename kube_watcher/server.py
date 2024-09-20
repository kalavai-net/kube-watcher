import os
from typing import List
import logging

from starlette.requests import Request
from fastapi import FastAPI, HTTPException, Depends
# import anvil.server
# import anvil.users

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
    GetLabelledResourcesRequest,
    FlowDeploymentRequest,
    AgentBuilderDeploymentRequest,
    UserRequest,
    CustomObjectDeploymentRequest,
    PodsWithStatusRequest,
    ServiceWithLabelRequest
)
from kube_watcher.kube_core import (
    KubeAPI
)
from kube_watcher.prometheus_core import PrometheusAPI




logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

IN_CLUSTER = "True" == os.getenv("IN_CLUSTER", "True")
PROMETHEUS_ENDPOINT = os.getenv("PROMETHEUS_ENDPOINT", "http://10.43.164.196:9090")
OPENCOST_ENDPOINT = os.getenv("OPENCOST_ENDPOINT", "http://10.43.53.194:9003")
#ANVIL_UPLINK_KEY = os.getenv("ANVIL_UPLINK_KEY", "")

USE_AUTH = not os.getenv("KW_USE_AUTH", "True").lower() in ("false", "0", "f", "no")
MASTER_KEY = os.getenv("KW_MASTER_KEY")
print(USE_AUTH)
if USE_AUTH:
    assert MASTER_KEY is not None, "If you are using auth, you must set a master key using the 'KW_MASTER_KEY' environment variable."
else:
    logger.warning("Warning: Authentication is disabled. This should only be used for testing.")

# API Key Validation
async def verify_api_key(request: Request):
    if not USE_AUTH:
        return
    api_key = request.headers.get("X-API-KEY")
    if api_key != MASTER_KEY:
        print(api_key, MASTER_KEY)
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

#anvil.server.connect(ANVIL_UPLINK_KEY)

kube_api = KubeAPI(in_cluster=IN_CLUSTER)
app = FastAPI()

@app.post("/v1/validate_user")
async def login(request: UserRequest):
    try:
        #user = anvil.users.login_with_email(request.email, request.password, remember=False)
        user = {"username": "User"}
        return {"username": user["username"], "error": None}
    except Exception as e:
        return {"error": str(e)}


@app.get("/v1/get_cluster_total_resources")
async def total_resources(api_key: str = Depends(verify_api_key)):
    cluster_capacity = kube_api.get_total_allocatable_resources()
    return cluster_capacity

@app.get("/v1/get_cluster_available_resources")
async def available_resources(api_key: str = Depends(verify_api_key)):
    cluster_capacity = kube_api.get_available_resources()
    return cluster_capacity

@app.get("/v1/get_cluster_labels")
async def cluster_labels(api_key: str = Depends(verify_api_key)):
    labels = kube_api.extract_cluster_labels()
    return labels

@app.post("/v1/get_node_labels")
async def node_labels(request: NodeLabelsRequest, api_key: str = Depends(verify_api_key)):
    labels = kube_api.get_node_labels(node_names=request.node_names)
    return labels

@app.post("/v1/get_pods_with_status")
async def pods_with_status(request: PodsWithStatusRequest, api_key: str = Depends(verify_api_key)):
    if request.node_names is None:
        node_names = kube_api.get_nodes()
    pods = []
    for name in node_names:
        pods.extend(
            kube_api.get_pods_with_status(
                node_name=name,
                statuses=request.statuses
            )
        )
    return pods

@app.get("/v1/get_nodes")
async def get_nodes(api_key: str = Depends(verify_api_key)):
    return kube_api.get_nodes_states()


@app.post("/v1/get_objects_of_type")
async def get_deployment_type(request: CustomObjectDeploymentRequest, api_key: str = Depends(verify_api_key)):
    objects = kube_api.kube_get_custom_objects(
        group=request.group,
        api_version=request.api_version,
        plural=request.plural)
    return objects

@app.post("/v1/get_ports_for_services")
async def get_ports_for_services(request: ServiceWithLabelRequest, api_key: str = Depends(verify_api_key)):
    services = kube_api.get_ports_for_services(
        label_key=request.label,
        label_value=request.value,
        types=request.types
    )
    return services


@app.post("/v1/get_node_stats")
async def node_stats(request: NodeStatusRequest, api_key: str = Depends(verify_api_key)):
    client = PrometheusAPI(url=PROMETHEUS_ENDPOINT, disable_ssl=True) # works as long as we are port forwarding from control plane
    
    return client.get_node_stats(
        node_id=request.node_id,
        start_time=request.start_time,
        end_time=request.end_time,
        chunk_size=request.chunk_size
    )


@app.post("/v1/get_nodes_cost")
async def node_cost(request: NodeCostRequest, api_key: str = Depends(verify_api_key)):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_nodes_computation(
        nodes=request.node_names,
        **request.kubecost_params.model_dump())


@app.post("/v1/get_namespaces_cost")
async def namespace_cost(request: NamespacesCostRequest, api_key: str = Depends(verify_api_key)):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_namespaces_cost(
        namespaces=request.namespace_names,
        **request.kubecost_params.model_dump())
    

@app.post("/v1/deploy_flow")
async def deploy_flow(request: FlowDeploymentRequest, api_key: str = Depends(verify_api_key)):
    """Todo"""
    response = kube_api.deploy_flow(
        deployment_name=request.deployment_name,
        namespace=request.namespace,
        flow_id=request.flow_id,
        flow_url=request.flow_url,
        num_cores=request.num_cores,
        ram_memory=request.ram_memory,
        api_key=request.api_key
    )
    return response

@app.post("/v1/delete_flow")
async def delete_flow(request: FlowDeploymentRequest, api_key: str = Depends(verify_api_key)):
    """Todo"""
    response = kube_api.delete_flow(
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )
    return response

@app.post("/v1/list_flows")
async def list_flows(namespace: str, api_key: str = Depends(verify_api_key)):
    response = kube_api.list_deployments(
        namespace=namespace
    )
    return response

@app.post("/v1/deploy_agent_builder")
async def deploy_agent_builder(request: AgentBuilderDeploymentRequest, api_key: str = Depends(verify_api_key)):
    """Todo"""
    response = kube_api.deploy_agent_builder(
        deployment_name=request.deployment_name,
        username=request.username,
        namespace=request.namespace,
        password=request.password,
        num_cores=request.num_cores,
        ram_memory=request.ram_memory,
        storage_memory=request.storage_memory,
        replicas=request.replicas
    )
    return response

@app.post("/v1/list_agent_builders")
async def list_agent_builders(namespace: str, api_key: str = Depends(verify_api_key)):
    """Todo: now just returns any deployment"""
    response = kube_api.list_deployments(
        namespace=namespace
    )
    return response


@app.post("/v1/delete_agent_builder")
async def delete_agent_builder(request: AgentBuilderDeploymentRequest, api_key: str = Depends(verify_api_key)):
    """Todo"""
    response = kube_api.delete_agent_builder(
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )
    return response


#### GENERIC_DEPLOYMENT
@app.post("/v1/deploy_generic_model")
async def deploy_ray_model(request: GenericDeploymentRequest, api_key: str = Depends(verify_api_key)):
    return kube_api.deploy_generic_model(request.config) 

@app.post("/v1/deploy_custom_object")
async def deploy_custom_objectl(request: CustomObjectDeploymentRequest, api_key: str = Depends(verify_api_key)):
    response = kube_api.kube_deploy_custom_object(
        group=request.group,
        api_version=request.api_version,
        namespace=request.namespace,
        plural=request.plural,
        body=request.body) 
    return response

@app.post("/v1/delete_labeled_resources")
async def delete_labeled_resources(request: DeleteLabelledResourcesRequest, api_key: str = Depends(verify_api_key)):
    return kube_api.delete_labeled_resources(request.namespace, request.label, request.value)

@app.post("/v1/get_resources_with_label")
async def get_resources_with_label(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_api_key)):
    return kube_api.find_resources_with_label(request.namespace, request.label, request.value)

@app.post("/v1/find_nodeport_url")
async def find_nodeport_url(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_api_key)):
    return kube_api.find_nodeport_url(request.namespace, request.label, request.value)

# Endpoint to check health
@app.get("/v1/health")
async def health():
    return HTTPException(status_code=200, detail="OK")

## DEPRECATED ##
# Create model deployment with deepsparse
@app.post("/v1/deploy_deepsparse_model")
async def namespace_cost(request: DeepsparseDeploymentRequest, api_key: str = Depends(verify_api_key)):
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
async def namespace_cost(request: DeepsparseDeploymentDeleteRequest, api_key: str = Depends(verify_api_key)):
    model_response = kube_api.delete_deepsparse_model(
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )
    return model_response

@app.post("/v1/list_deepsparse_deployments")
async def namespace_cost(request: DeepsparseDeploymentListRequest, api_key: str = Depends(verify_api_key)):
    model_response = kube_api.list_deepsparse_deployments(
        namespace=request.namespace
    )
    return model_response


