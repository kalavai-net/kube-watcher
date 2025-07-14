import os
import argparse
from typing import List
import logging
import requests
import yaml

import uvicorn
from starlette.requests import Request
from fastapi import FastAPI, HTTPException, Depends
from fastapi_mcp import FastApiMCP

from kube_watcher.cost_core import OpenCostAPI

from kube_watcher.models import (
    NodeStatusRequest,
    NodesRequest,
    NodeCostRequest,
    NamespacesCostRequest,
    GenericDeploymentRequest,
    DeleteLabelledResourcesRequest,
    GetLabelledResourcesRequest,
    JobTemplateRequest,
    CustomJobTemplateRequest,
    CustomObjectDeploymentRequest,
    PodsWithStatusRequest,
    ServiceWithLabelRequest,
    CustomObjectRequest,
    StorageClaimRequest,
    ServiceRequest,
    StorageRequest,
    RayClusterRequest,
    UserWorkspaceRequest,
    NodeLabelsRequest
)
from kube_watcher.kube_core import (
    KubeAPI
)
from kube_watcher.utils import extract_auth_token
from kube_watcher.prometheus_core import PrometheusAPI
from kube_watcher.jobs import Job, JobTemplate
from kube_watcher.ray_cluster import RayCluster


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

USE_AUTH = not os.getenv("KW_USE_AUTH", "True").lower() in ("false", "0", "f", "no")
ADMIN_KEY = os.getenv("KW_ADMIN_KEY") # all permissions
WRITE_KEY = os.getenv("KW_WRITE_KEY") # deploy and read permissions
READ_ONLY_KEY = os.getenv("KW_READ_ONLY_KEY") # read permissions

KALAVAI_USER_KEY = os.getenv("KALAVAI_USER_KEY", "kalavai.cluster.user")

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
        return None
    api_key = extract_auth_token(headers=request.headers)
    if "error" in api_key:
        raise HTTPException(status_code=401, detail=f"Error when extracting auth token: {api_key}")
    if api_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail=f"Request requires Admin API Key.")
    return api_key

async def verify_read_key(request: Request):
    if not USE_AUTH:
        return None
    api_key = extract_auth_token(headers=request.headers)
    if "error" in api_key:
        raise HTTPException(status_code=401, detail=f"Error when extracting auth token: {api_key}")
    if api_key != READ_ONLY_KEY and api_key != ADMIN_KEY and api_key != WRITE_KEY:
        raise HTTPException(status_code=401, detail=f"Request requires a Read API Key")
    return api_key

async def verify_write_key(request: Request):
    if not USE_AUTH:
        return None
    api_key = extract_auth_token(headers=request.headers)
    if "error" in api_key:
        raise HTTPException(status_code=401, detail=f"Error when extracting auth token: {api_key}")
    if api_key != WRITE_KEY and api_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail=f"Request requires a User API Key")
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
        # TODO: Implement user key validation
        validated = True

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
        # TODO: Implement user key validation
        validated = True

        if not validated:
            raise HTTPException(status_code=401, detail="User Key is not authorised")
        return user.lower()
    except:
        raise HTTPException(status_code=401, detail="User Key is not authorised")

async def verify_force_namespace(request: Request):
    """Only admin keys can force namespace"""
    if not USE_AUTH:
        return True
    api_key = extract_auth_token(headers=request.headers)
    return api_key == ADMIN_KEY
#############################


@app.get("/v1/get_cluster_total_resources", 
    operation_id="get_cluster_total_resources",
    summary="Get all resources available in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets information regarding all resources (CPU, GPU, memory, etc.) in the kalavai pool. This helps identify resource availability",
    response_description="Resource information for the kalavai pool")
async def total_resources(request: NodesRequest, api_key: str = Depends(verify_read_key)):
    cluster_capacity = kube_api.get_total_allocatable_resources(node_names=request.node_names)
    return cluster_capacity

@app.get("/v1/get_cluster_available_resources", 
    operation_id="get_cluster_available_resources",
    summary="Get available resources in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets information regarding available resources (CPU, GPU, memory, etc.) in the kalavai pool. This helps identify if there are resources available for deployments",
    response_description="Resource information for the kalavai pool")
async def available_resources(request: NodesRequest, api_key: str = Depends(verify_read_key)):
    cluster_capacity = kube_api.get_available_resources(node_names=request.node_names)
    return cluster_capacity

@app.get("/v1/get_cluster_labels", 
    operation_id="get_cluster_labels",
    summary="Get labels for the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets labels for the kalavai pool",
    response_description="Labels for the kalavai pool")
async def cluster_labels(api_key: str = Depends(verify_read_key)):
    labels = kube_api.extract_cluster_labels()
    return labels

@app.post("/v1/get_node_labels", 
    operation_id="get_node_labels",
    summary="Get labels associated with a set of nodes in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets labels associated with a set of nodes in the kalavai pool",
    response_description="Labels for the nodes in the kalavai pool")
async def node_labels(request: NodesRequest, api_key: str = Depends(verify_read_key)):
    labels = kube_api.get_node_labels(node_names=request.node_names)
    return labels

@app.post("/v1/get_node_gpus", 
    operation_id="get_node_gpus",
    summary="Get GPU details (model, count, memory) associated with a set of nodes in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets GPU details associated with a set of nodes in the kalavai pool",
    response_description="GPUs for the nodes in the kalavai pool")
async def node_gpus(request: NodesRequest, api_key: str = Depends(verify_read_key)):
    labels = kube_api.get_node_gpus(node_names=request.node_names)
    return labels

@app.post("/v1/get_pods_with_status", 
    operation_id="get_pods_with_status",
    summary="Get pods with a given status within a set of nodes in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets pods with a given status within a set of nodes in the kalavai pool",
    response_description="Pods with the given status for the nodes in the kalavai pool")
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

@app.get("/v1/get_nodes", 
    operation_id="get_nodes",
    summary="Get connected nodes in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets connected nodes in the kalavai pool",
    response_description="Nodes in the kalavai pool")
async def get_nodes(api_key: str = Depends(verify_read_key)):
    return kube_api.get_nodes_states()

@app.post("/v1/get_nodes_resources", 
    operation_id="get_nodes_resources",
    summary="Get resource usage for a set of nodes in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets resource usage for a set of nodes in the kalavai pool",
    response_description="Resource usage for the nodes in the kalavai pool")
async def get_nodes_resources(request: NodesRequest, api_key: str = Depends(verify_read_key)):
    if request.node_names is None:
        if request.node_labels is None:
            raise HTTPException(status_code=400, detail="node_names or node_labels must be provided")
        
        request.node_names = kube_api.get_nodes_with_labels(
            labels=request.node_labels)
    return kube_api.get_nodes_resources(node_names=request.node_names)

@app.post("/v1/get_node_stats", 
    operation_id="get_node_stats",
    summary="Get node runtime stats for a set of nodes in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets node runtime stats for a set of nodes in the kalavai pool",
    response_description="Node runtime stats for the nodes in the kalavai pool")
async def node_stats(request: NodeStatusRequest, api_key: str = Depends(verify_read_key)):
    client = PrometheusAPI(url=PROMETHEUS_ENDPOINT, disable_ssl=True) # works as long as we are port forwarding from control plane

    if request.node_names is None:
        if request.node_labels is None:
            raise HTTPException(status_code=400, detail="node_names or node_labels must be provided")
        
        request.node_names = kube_api.get_nodes_with_labels(
            labels=request.node_labels)
    
    result = {
        name: client.get_node_stats(
            node_id=name,
            start_time=request.start_time,
            end_time=request.end_time,
            chunk_size=request.chunk_size
        )
        for name in request.node_names
    }
    return result

@app.post("/v1/delete_nodes", 
    operation_id="delete_nodes",
    summary="Delete, or disconnects, a set of nodes from the Kalavai compute pool",
    tags=["pool_management"],
    description="Disconnects a set of nodes from the kalavai pool",
    response_description="None")
async def delete_nodes(request: NodesRequest, api_key: str = Depends(verify_admin_key)):
    for node in request.node_names:
        kube_api.delete_node(node)
    return None


@app.post("/v1/set_node_schedulable", 
    operation_id="set_node_schedulable",
    summary="Set the schedulable state of a set of nodes in the Kalavai compute pool",
    tags=["pool_management"],
    description="Sets the schedulable state of a set of nodes in the kalavai pool. If a node is set to unschedulable, the pool will not schedule new workloads on it.",
    response_description="None")
async def set_nodes_schedulable(request: NodesRequest, api_key: str = Depends(verify_admin_key)):
    for node in request.node_names:
        kube_api.set_node_schedulable(node_name=node, state=request.schedulable)
    return None

@app.post("/v1/add_labels_to_node", 
    operation_id="add_labels_to_node",
    summary="Add labels (key-value pairs) to a specific node",
    tags=["pool_management"],
    description="Adds labels (key-value pairs) to a specific node, by name",
    response_description="None")
async def add_labels_to_node(request: NodeLabelsRequest, api_key: str = Depends(verify_admin_key)):
    """
    Add labels to a specific node by its name.
    """
    success = kube_api.add_labels_to_node(
        node_name=request.node_name,
        new_labels=request.labels
    )
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to add labels to node {request.node_name}")
    
    return {"status": "success", "message": f"Labels added to node {request.node_name}"}

@app.post("/v1/get_storage_usage", 
    operation_id="get_storage_usage",
    summary="Get storage usage for a set of namespaces in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets storage usage for a set of namespaces in the kalavai pool",
    response_description="Storage usage for the namespaces in the kalavai pool")
async def get_storage_usage(request: StorageRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_objects = {}
    for namespace in namespaces:
        ns_objects[namespace] = kube_api.get_storage_usage(namespace=namespace, target_storages=request.names)
    return ns_objects

@app.post("/v1/get_objects_of_type", 
    operation_id="get_objects_of_type",
    summary="Get objects of a given type in a set of namespaces in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets objects of a given type in a set of namespaces in the kalavai pool",
    response_description="Objects of the given type in the namespaces in the kalavai pool")
async def get_deployment_type(request: CustomObjectRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_objects = {}
    for namespace in namespaces:
        ns_objects[namespace] = kube_api.kube_get_custom_objects(
            group=request.group,
            namespace=namespace,
            api_version=request.api_version,
            plural=request.plural)
    return ns_objects


@app.post("/v1/get_status_for_object", 
    operation_id="get_status_for_object",
    summary="Get status for a given object in a set of namespaces in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets status for a given object in a set of namespaces in the kalavai pool",
    response_description="Status for the given object in the namespaces in the kalavai pool")
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


@app.post("/v1/get_logs_for_label", 
    operation_id="get_logs_for_label",
    summary="Get logs for a given label in a set of namespaces in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets logs for a given label in a set of namespaces in the kalavai pool",
    response_description="Logs for the given label in the namespaces in the kalavai pool")
async def get_logs_for_label(request: GetLabelledResourcesRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_read_key), namespace: str = Depends(verify_write_namespace)):
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    logs = kube_api.get_logs_for_labels(
        namespace=namespace,
        label_key=request.label,
        label_value=request.value)
    return logs

@app.post("/v1/describe_pods_for_label", 
    operation_id="describe_pods_for_label",
    summary="Describe pods for a given label in a set of namespaces in the Kalavai compute pool",
    tags=["workload_info"],
    description="Describes pods for a given label in a set of namespaces in the kalavai pool",
    response_description="Pods for the given label in the namespaces in the kalavai pool")
async def describe_pods_for_label(request: GetLabelledResourcesRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_read_key), namespace: str = Depends(verify_write_namespace)):
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    logs = kube_api.describe_pods_for_labels(
        namespace=namespace,
        label_key=request.label,
        label_value=request.value)
    return logs

@app.post("/v1/get_pods_status_for_label", 
    operation_id="get_pods_status_for_label",
    summary="Get pods status for a given label in a set of namespaces in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets pods status for a given label in a set of namespaces in the kalavai pool",
    response_description="Pods status for the given label in the namespaces in the kalavai pool")
async def get_pods_status_for_label(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_logs = {}
    for namespace in namespaces:
        ns_logs[namespace] = kube_api.get_pods_status_for_label(
            namespace=namespace,
            label_key=request.label,
            label_value=request.value)
    return ns_logs


@app.post("/v1/get_ports_for_services", 
    operation_id="get_ports_for_services",
    summary="Get ports for services for a given label in a set of namespaces in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets ports for services for a given label in a set of namespaces in the kalavai pool",
    response_description="Ports for the services for the given label in the namespaces in the kalavai pool")
async def get_ports_for_services(request: ServiceWithLabelRequest, api_key: str = Depends(verify_read_key)):
    services = kube_api.get_ports_for_services(
        label_key=request.label,
        label_value=request.value,
        types=request.types
    )
    return services

@app.post("/v1/get_deployments", 
    operation_id="get_deployments",
    summary="Get job and model deployments for a set of namespaces in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets job and model deployments for a set of namespaces in the kalavai pool",
    response_description="Deployments for the namespaces in the kalavai pool")
async def get_deployments(api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_deployments = {}
    for namespace in namespaces:
        ns_deployments[namespaces] = kube_api.list_deployments(
            namespace=namespace
        )
    return ns_deployments


@app.post("/v1/get_nodes_cost", 
    operation_id="get_nodes_cost",
    summary="Get cost for a set of nodes in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets cost (from node usage) for a set of nodes in the kalavai pool as monitored by kubecost.",
    response_description="Cost for the nodes in the kalavai pool")
async def node_cost(request: NodeCostRequest, api_key: str = Depends(verify_read_key)):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    if request.node_names is None:
        if request.node_labels is None:
            raise HTTPException(status_code=400, detail="node_names or node_labels must be provided")
        
        request.node_names = kube_api.get_nodes_with_labels(
            labels=request.node_labels
        )
    print(f"Getting cost for nodes: {request.node_names}")

    return opencost.get_nodes_computation(
        nodes=request.node_names,
        **request.kubecost_params.model_dump())

@app.post("/v1/get_namespaces_cost", 
    operation_id="get_namespaces_cost",
    summary="Get cost for a set of namespaces in the Kalavai compute pool",
    tags=["pool_info"],
    description="Gets cost (from namespace usage) for a set of namespaces in the kalavai pool as monitored by kubecost.",
    response_description="Cost for the namespaces in the kalavai pool")
async def namespace_cost(request: NamespacesCostRequest, api_key: str = Depends(verify_read_key)):
    opencost = OpenCostAPI(base_url=OPENCOST_ENDPOINT)

    return opencost.get_namespaces_cost(
        namespaces=request.namespace_names,
        **request.kubecost_params.model_dump())

@app.post("/v1/create_user_space", 
    operation_id="create_user_space",
    summary="Create a user workspace in the Kalavai compute pool",
    tags=["pool_management"],
    description="Creates a user workspace in the kalavai pool",
    response_description="None")
async def create_user_space(request: UserWorkspaceRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_read_key), namespace: str = Depends(verify_write_namespace)):
    # create namespace for user
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    
    kube_api.create_namespace(
        name=namespace,
        labels={"monitor-pods-datasets": "enabled"})

    # add annotation to user node
    if request.user_id is not None and request.node_name is not None:
        kube_api.add_annotation_to_node(
            node_labels={"kubernetes.io/hostname": request.node_name},
            annotation={KALAVAI_USER_KEY: request.user_id}
        )

    try:
        # deploy for new workspace
        kube_api.deploy_generic_model(request.config, force_namespace=namespace)
    except Exception as e:
        return {"status": str(e)}
    return {"status": "success"}

@app.get("/v1/get_job_templates", 
    operation_id="get_job_templates",
    summary="Get available job and model engine templates in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets available job and model engine templates in the kalavai pool",
    response_description="Job templates in the kalavai pool")
async def get_job_templates(type: str=None, api_key: str = Depends(verify_read_key)):
    model_templates = []
    for e in JobTemplate:
        if type is None:
            model_templates.append(e.name)
        else:
            job = await get_job_defaults(request=JobTemplateRequest(template=e.name))
            if "error" in job:
                continue
            if job["metadata"]["type"] == type:
                model_templates.append(e.name)
    return model_templates

@app.get("/v1/job_defaults", 
    operation_id="get_job_defaults",
    summary="Get default values for a job template in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets default values for a job template in the kalavai pool",
    response_description="Default values for the job template in the kalavai pool")
async def get_job_defaults(request: JobTemplateRequest, api_key: str = Depends(verify_read_key)):
    try:
        job = Job(template=request.template)
        return {
            "defaults": job.get_defaults(),
            "metadata": job.get_metadata()
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/v1/deploy_job", 
    operation_id="deploy_job",
    summary="Deploy a job from a job or model engine template in the Kalavai compute pool",
    tags=["workload_management"],
    description="Deploys a job from a job or model engine template in the kalavai pool",
    response_description="None")
async def deploy_job(request: JobTemplateRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_write_key), namespace: str = Depends(verify_write_namespace)):
    # populate template with values
    job = Job(template=request.template)
    deployment = job.populate(
        values=request.template_values,
        target_labels=request.target_labels)
    
    print("-> Deployment parsed: ", deployment)
    
    # deploy job
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    responses = []
    responses.append(kube_api.kube_deploy_custom_object(
        group="batch.volcano.sh",
        api_version="v1alpha1",
        plural="jobs",
        body=deployment,
        namespace=namespace
    ))
    # deploy service
    if job.ports is not None and len(job.ports) > 0:
        request = ServiceRequest(
            name=f"{job.job_name}-service",
            labels=job.job_label,
            selector_labels={ **job.job_label, **{"role": "leader"} },
            service_type="NodePort",
            ports=[{"name": f"http-{port}", "port": int(port), "protocol": "TCP", "target_port": int(port)} for port in job.ports])
        responses.append(kube_api.deploy_service(
            namespace=namespace,
            **request.model_dump()
        ))
    return responses

@app.post("/v1/deploy_custom_job", 
    operation_id="deploy_custom_job",
    summary="Deploy a job from a custom job template in the Kalavai compute pool",
    tags=["workload_management"],
    description="Deploys a job from a custom job template in the kalavai pool",
    response_description="None")
async def deploy_job_dev(request: CustomJobTemplateRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_admin_key), namespace: str = Depends(verify_write_namespace)):
    # populate template with values
    job = Job.from_yaml(template_str=request.template)
    yaml_defaults = yaml.safe_load(request.default_values)
    deployment = job.populate(
        values=request.template_values,
        default_values=yaml_defaults,
        target_labels=request.target_labels)
    print("--->", deployment)
    
    # deploy job
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    response = kube_api.kube_deploy_custom_object(
        group="batch.volcano.sh",
        api_version="v1alpha1",
        plural="jobs",
        body=deployment,
        namespace=namespace
    )
    print("--->", response)
    # deploy service
    if job.ports is not None and len(job.ports) > 0:
        request = ServiceRequest(
            name=f"{job.job_name}-service",
            labels=job.job_label,
            selector_labels={ **job.job_label, **{"role": "leader"} },
            service_type="NodePort",
            ports=[{"name": f"http-{port}", "port": int(port), "protocol": "TCP", "target_port": int(port)} for port in job.ports])
        response = kube_api.deploy_service(
            namespace=namespace,
            **request.model_dump()
        )
    return response

@app.post("/v1/deploy_ray", 
    operation_id="deploy_ray",
    summary="Deploy a Ray cluster in the Kalavai compute pool",
    tags=["workload_management"],
    description="Deploys a Ray cluster in the kalavai pool",
    response_description="None")
async def deploy_ray(request: RayClusterRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_write_key), namespace: str = Depends(verify_write_namespace)):
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    
    cluster = RayCluster(name=request.name, manifest=request.manifest)
    response = kube_api.kube_deploy_custom_object(
        group="ray.io",
        api_version="v1",
        plural="rayclusters",
        body=cluster.body,
        namespace=namespace
    )
    return response

#### GENERIC_DEPLOYMENT
@app.post("/v1/deploy_generic_model", 
    operation_id="deploy_generic_model",
    summary="Deploy a generic model in the Kalavai compute pool",
    tags=["workload_management"],
    description="Deploys a generic model in the kalavai pool",
    response_description="None")
async def deploy_generic_model(request: GenericDeploymentRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_admin_key)):
    if can_force_namespace and request.force_namespace is not None:
        return kube_api.deploy_generic_model(request.config, force_namespace=request.force_namespace)
    else:
        return kube_api.deploy_generic_model(request.config) 

@app.post("/v1/deploy_custom_object", 
    operation_id="deploy_custom_object",
    summary="Deploy a custom object in the Kalavai compute pool",
    tags=["workload_management"],
    description="Deploys a custom object in the kalavai pool",
    response_description="None")
async def deploy_custom_object(request: CustomObjectDeploymentRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_write_key), namespace: str = Depends(verify_write_namespace)):
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    response = kube_api.kube_deploy_custom_object(
        group=request.object.group,
        api_version=request.object.api_version,
        namespace=namespace,
        plural=request.object.plural,
        body=request.body) 
    return response

@app.post("/v1/deploy_storage_claim", 
    operation_id="deploy_storage_claim",
    summary="Deploy a storage claim in the Kalavai compute pool",
    tags=["workload_management"],
    description="Deploys a storage claim in the kalavai pool",
    response_description="None")
async def deploy_storage_claim(request: StorageClaimRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_admin_key), namespace: str = Depends(verify_write_namespace)):
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    response = kube_api.deploy_storage_claim(
        namespace=namespace,
        **request.model_dump())
    return response

@app.post("/v1/deploy_service", 
    operation_id="deploy_service",
    summary="Deploy a service in the Kalavai compute pool",
    tags=["workload_management"],
    description="Deploys a service in the kalavai pool",
    response_description="None")
async def deploy_service(request: ServiceRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_write_key), namespace: str = Depends(verify_write_namespace)):
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    response = kube_api.deploy_service(
        namespace=namespace,
        **request.model_dump())
    return response

@app.post("/v1/delete_labeled_resources", 
    operation_id="delete_labeled_resources",
    summary="Delete resources with a given label in the Kalavai compute pool",
    tags=["workload_management"],
    description="Deletes resources with a given label in the kalavai pool",
    response_description="None")
async def delete_labeled_resources(request: DeleteLabelledResourcesRequest, can_force_namespace: bool = Depends(verify_force_namespace), api_key: str = Depends(verify_write_key), namespace: str = Depends(verify_write_namespace)):
    if can_force_namespace and request.force_namespace is not None:
        namespace = request.force_namespace
    return kube_api.delete_labeled_resources(namespace, request.label, request.value)

@app.post("/v1/get_resources_with_label", 
    operation_id="get_resources_with_label",
    summary="Get resources with a given label in the Kalavai compute pool",
    tags=["workload_info"],
    description="Gets resources with a given label in the kalavai pool",
    response_description="Resources with the given label in the kalavai pool")
async def get_resources_with_label(request: GetLabelledResourcesRequest, api_key: str = Depends(verify_read_key), namespaces: str = Depends(verify_read_namespaces)):
    ns_resources = {}
    for namespace in namespaces:
        ns_resources[namespace] = kube_api.find_resources_with_label(
            namespace,
            request.label,
            request.value)
    return ns_resources

# Endpoint to check health
@app.get("/v1/health", 
    operation_id="health",
    summary="Check the health of the Kalavai compute pool",
    tags=["pool_info"],
    description="Checks the health of the kalavai pool",
    response_description="OK")
async def health():
    return HTTPException(status_code=200, detail="OK")

### BUILD MCP WRAPPER ###
mcp = FastApiMCP(
    app,
    name="Kalavai pool MCP",
    exclude_tags=[
        "pool_management",
        "workload_management"
    ]
)
mcp.mount()
##########################

def run_api(host="0.0.0.0", port=8000, log_level="critical"):
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log_level", type=str, default="critical")
    args = parser.parse_args()
    run_api(
        host=args.host,
        port=args.port,
        log_level=args.log_level
    )
