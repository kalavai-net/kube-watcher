import os
from typing import List
import logging
import requests

from starlette.requests import Request
from fastapi import FastAPI, HTTPException, Depends
# import anvil.server
# import anvil.users

from kube_watcher.cost_core import OpenCostAPI

from kube_watcher.models import (
    NodeStatusRequest,
    NodesRequest,
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
    ServiceWithLabelRequest,
    CustomObjectRequest,
    StorageClaimRequest,
    ServiceRequest,
    StorageRequest
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

IN_CLUSTER = not os.getenv("IN_CLUSTER", "True").lower() in ("false", "0", "f", "no")
KALAVAI_API_ENDPOINT = os.getenv("KALAVAI_API_ENDPOINT", "https://platform.kalavai.net/_/api")
PROMETHEUS_ENDPOINT = os.getenv("PROMETHEUS_ENDPOINT", "prometheus-server.prometheus-system.svc.cluster.local:80")
OPENCOST_ENDPOINT = os.getenv("OPENCOST_ENDPOINT", "opencost.opencost.svc.cluster.local:9003")
IS_SHARED_POOL = not os.getenv("IS_SHARED_POOL", "True").lower() in ("false", "0", "f", "no")
ALLOW_UNREGISTERED_USER = not os.getenv("ALLOW_UNREGISTERED_USER", "True").lower() in ("false", "0", "f", "no")
#ANVIL_UPLINK_KEY = os.getenv("ANVIL_UPLINK_KEY", "")

USE_AUTH = not os.getenv("KW_USE_AUTH", "True").lower() in ("false", "0", "f", "no")
ADMIN_KEY = os.getenv("KW_ADMIN_KEY") # all permissions
WRITE_KEY = os.getenv("KW_WRITE_KEY") # deploy and read permissions
READ_ONLY_KEY = os.getenv("KW_READ_ONLY_KEY") # read permissions


kube_api = KubeAPI(in_cluster=IN_CLUSTER)
app = FastAPI()

    
if USE_AUTH:
    for key in [ADMIN_KEY, WRITE_KEY, READ_ONLY_KEY]:
        name = f"{key=}".split("=")[0]
        assert key is not None, f"If you are using auth, you must set ADMIN_KEY, WRITE_KEY and READ_ONLY_KEY via env var"
else:
    logger.warning("Warning: Authentication is disabled. This should only be used for testing.")

################################
## API Key Validation methods ##
################################
async def verify_admin_key(request: Request):
    if not USE_AUTH:
        return
    api_key = request.headers.get("X-API-KEY")
    if api_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Request requires Admin API Key")
    return api_key

async def verify_read_key(request: Request):
    if not USE_AUTH:
        return
    api_key = request.headers.get("X-API-KEY")
    if api_key != READ_ONLY_KEY and api_key != ADMIN_KEY and api_key != WRITE_KEY:
        raise HTTPException(status_code=401, detail="Request requires a Read API Key")
    return api_key

async def verify_write_key(request: Request):
    if not USE_AUTH:
        return
    api_key = request.headers.get("X-API-KEY")
    if api_key != WRITE_KEY and api_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Request requires a User API Key")
    return api_key

async def verify_read_namespaces(request: Request):
    """If shared pool, all users see each other's work"""
    if IS_SHARED_POOL:
        return kube_api.list_namespaces()
    if ALLOW_UNREGISTERED_USER:
        return ["default"]
    api_key = request.headers.get("USER-KEY")
    user = request.headers.get("USER", None)
    
    try:
        response = requests.request(
            method="post",
            url=f"{KALAVAI_API_ENDPOINT}/validate_user_namespace/{user}",
            data={"key": api_key}
        ).json()
        validated = response["success"] in ["true", "True"]

        if not validated:
            raise HTTPException(status_code=401, detail="User Key is not authorised")
        namespaces = [user.lower()]
        print(f"Verified read namespaces: {namespaces}")
        return namespaces
    except:
        raise HTTPException(status_code=401, detail="User Key is not authorised")

async def verify_write_namespace(request: Request):
    """Users only have write access to their namespace (all default if ALLOW_UNREGISTERED_USER)"""
    api_key = request.headers.get("USER-KEY")
    user = request.headers.get("USER", None)
    if ALLOW_UNREGISTERED_USER:
        return "default"
    
    try:
        response = requests.request(
            method="post",
            url=f"{KALAVAI_API_ENDPOINT}/validate_user_namespace/{user}",
            data={"key": api_key}
        ).json()
        validated = response["success"] in ["true", "True"]

        if not validated:
            raise HTTPException(status_code=401, detail="User Key is not authorised")
        return user.lower()
    except:
        raise HTTPException(status_code=401, detail="User Key is not authorised")
#############################


@app.post("/v1/validate_user")
async def login(request: UserRequest):
    try:
        #user = anvil.users.login_with_email(request.email, request.password, remember=False)
        user = {"username": "User"}
        return {"username": user["username"], "error": None}
    except Exception as e:
        return {"error": str(e)}


@app.get("/v1/get_cluster_total_resources")
async def total_resources(api_key: str = Depends(verify_read_key)):
    cluster_capacity = kube_api.get_total_allocatable_resources()
    return cluster_capacity

@app.get("/v1/get_cluster_available_resources")
async def available_resources(api_key: str = Depends(verify_read_key)):
    cluster_capacity = kube_api.get_available_resources()
    return cluster_capacity

@app.get("/v1/get_cluster_labels")
async def cluster_labels(api_key: str = Depends(verify_read_key)):
    labels = kube_api.extract_cluster_labels()
    return labels

@app.post("/v1/get_node_labels")
async def node_labels(request: NodesRequest, api_key: str = Depends(verify_read_key)):
    labels = kube_api.get_node_labels(node_names=request.node_names)
    return labels

@app.post("/v1/get_node_gpus")
async def node_gpus(request: NodesRequest, api_key: str = Depends(verify_read_key)):
    labels = kube_api.get_node_gpus(node_names=request.node_names)
    return labels

@app.post("/v1/get_pods_with_status")
async def pods_with_status(request: PodsWithStatusRequest, api_key: str = Depends(verify_read_key)):
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
async def get_nodes(api_key: str = Depends(verify_read_key)):
    return kube_api.get_nodes_states()

@app.post("/v1/get_nodes_resources")
async def get_nodes_resources(request: NodesRequest, api_key: str = Depends(verify_read_key)):
    return kube_api.get_nodes_resources(node_names=request.node_names)


@app.post("/v1/delete_nodes")
async def delete_nodes(request: NodesRequest, api_key: str = Depends(verify_admin_key)):
    for node in request.node_names:
        kube_api.delete_node(node)
    return None


@app.post("/v1/set_node_schedulable")
async def set_nodes_schedulable(request: NodesRequest, api_key: str = Depends(verify_admin_key)):
    for node in request.node_names:
        kube_api.set_node_schedulable(node_name=node, state=request.schedulable)
    return None

@app.post("/v1/get_storage_usage")
async def get_storage_usage(request: StorageRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_objects = {}
    for namespace in namespaces:
        ns_objects[namespace] = kube_api.get_storage_usage(namespace=namespace, target_storages=request.names)
    return ns_objects

@app.post("/v1/get_objects_of_type")
async def get_deployment_type(request: CustomObjectRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_objects = {}
    for namespace in namespaces:
        ns_objects[namespace] = kube_api.kube_get_custom_objects(
            group=request.group,
            namespace=namespace,
            api_version=request.api_version,
            plural=request.plural)
    return ns_objects


@app.post("/v1/get_status_for_object")
async def get_status_for_object(request: CustomObjectRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_objects = {}
    for namespace in namespaces:
        objects = kube_api.kube_get_status_custom_object(
            group=request.group,
            api_version=request.api_version,
            plural=request.plural,
            namespace=namespace,
            name=request.name)
        if objects is not None:
            ns_objects[namespace] = objects
    return ns_objects

@app.post("/v1/get_logs_for_label")
async def get_logs_for_label(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_read_key), namespace: str = Depends(verify_write_namespace)):
    logs = kube_api.get_logs_for_labels(
        namespace=namespace,
        label_key=request.label,
        label_value=request.value)
    return logs

@app.post("/v1/describe_pods_for_label")
async def describe_pods_for_label(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_read_key), namespace: str = Depends(verify_write_namespace)):
    logs = kube_api.describe_pods_for_labels(
        namespace=namespace,
        label_key=request.label,
        label_value=request.value)
    return logs

@app.post("/v1/get_pods_status_for_label")
async def get_pods_status_for_label(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_logs = {}
    for namespace in namespaces:
        ns_logs[namespace] = kube_api.get_pods_status_for_label(
            namespace=namespace,
            label_key=request.label,
            label_value=request.value)
    return ns_logs


@app.post("/v1/get_ports_for_services")
async def get_ports_for_services(request: ServiceWithLabelRequest, api_key: str = Depends(verify_read_key)):
    services = kube_api.get_ports_for_services(
        label_key=request.label,
        label_value=request.value,
        types=request.types
    )
    return services

@app.post("/v1/get_deployments")
async def get_deployments(api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_deployments = {}
    for namespace in namespaces:
        ns_deployments[namespaces] = kube_api.list_deployments(
            namespace=namespace
        )
    return ns_deployments


@app.post("/v1/get_node_stats")
async def node_stats(request: NodeStatusRequest, api_key: str = Depends(verify_read_key)):
    client = PrometheusAPI(url=PROMETHEUS_ENDPOINT, disable_ssl=True) # works as long as we are port forwarding from control plane
    
    return client.get_node_stats(
        node_id=request.node_id,
        start_time=request.start_time,
        end_time=request.end_time,
        chunk_size=request.chunk_size
    )


@app.post("/v1/get_nodes_cost")
async def node_cost(request: NodeCostRequest, api_key: str = Depends(verify_read_key)):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_nodes_computation(
        nodes=request.node_names,
        **request.kubecost_params.model_dump())


@app.post("/v1/get_namespaces_cost")
async def namespace_cost(request: NamespacesCostRequest, api_key: str = Depends(verify_read_key)):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_namespaces_cost(
        namespaces=request.namespace_names,
        **request.kubecost_params.model_dump())

@app.post("/v1/create_user_space")
async def create_user_space(request: GenericDeploymentRequest, api_key: str = Depends(verify_read_key), namespace: str = Depends(verify_write_namespace)):
    # create namespace for user
    kube_api.create_namespace(
        name=namespace,
        labels={"monitor-pods-datasets": "enabled"})

    try:
        # deploy for new workspace
        kube_api.deploy_generic_model(request.config, force_namespace=namespace)
    except Exception as e:
        return {"status": str(e)}
    return {"status": "success"}


#### GENERIC_DEPLOYMENT
@app.post("/v1/deploy_generic_model")
async def deploy_generic_model(request: GenericDeploymentRequest, api_key: str = Depends(verify_admin_key)):
    return kube_api.deploy_generic_model(request.config) 

@app.post("/v1/deploy_custom_object")
async def deploy_custom_object(request: CustomObjectDeploymentRequest, api_key: str = Depends(verify_write_key), namespace: str = Depends(verify_write_namespace)):
    response = kube_api.kube_deploy_custom_object(
        group=request.object.group,
        api_version=request.object.api_version,
        namespace=namespace,
        plural=request.object.plural,
        body=request.body) 
    return response

@app.post("/v1/deploy_storage_claim")
async def deploy_storage_claim(request: StorageClaimRequest, api_key: str = Depends(verify_admin_key), namespace: str = Depends(verify_write_namespace)):
    response = kube_api.deploy_storage_claim(
        namespace=namespace,
        **request.model_dump())
    return response

@app.post("/v1/deploy_service")
async def deploy_service(request: ServiceRequest, api_key: str = Depends(verify_write_key), namespace: str = Depends(verify_write_namespace)):
    response = kube_api.deploy_service(
        namespace=namespace,
        **request.model_dump())
    return response

@app.post("/v1/delete_labeled_resources")
async def delete_labeled_resources(request: DeleteLabelledResourcesRequest, api_key: str = Depends(verify_write_key), namespace: str = Depends(verify_write_namespace)):
    return kube_api.delete_labeled_resources(namespace, request.label, request.value)

@app.post("/v1/get_resources_with_label")
async def get_resources_with_label(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_resources = {}
    for namespace in namespaces:
        ns_resources[namespace] = kube_api.find_resources_with_label(
            namespace,
            request.label,
            request.value)
    return ns_resources

@app.post("/v1/find_nodeport_url")
async def find_nodeport_url(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_ports = {}
    for namespace in namespaces:
        ns_ports[namespace] = kube_api.find_nodeport_url(
            namespace,
            request.label,
            request.value)
    return ns_ports

# Endpoint to check health
@app.get("/v1/health")
async def health():
    return HTTPException(status_code=200, detail="OK")

