from typing import List, Optional, Dict, Literal, Union
from pydantic import BaseModel
from enum import Enum

# This are off-the-shelf supported templates
class JobTemplate(Enum):
    custom = 0
    vllm = 1
    aphrodite = 2
    llamacpp = 3
    #petals = 4
    litellm = 5
    playground = 6
    #boinc = 7
    gpustack = 8
    speaches = 9
    sglang = 10
    #https = 11
    langfuse = 12
    n8n = 13
    flowise = 14
    diffusers = 15
    #axolotl = 16
    registrar = 17
    raycluster = 18
    #flexible = 99

class NodeStatusRequest(BaseModel):
    node_names: List[str] = None
    node_labels: dict = None
    start_time: str = "1h"
    end_time: str = "now"
    step: str = "1m"
    aggregate_results: bool = False

class StorageClaimRequest(BaseModel):
    name: str
    labels: dict
    access_modes: list
    storage_class_name: str
    storage_size: int
    force_namespace: str = None

class StorageRequest(BaseModel):
    names: list = None

class ServiceRequest(BaseModel):
    name: str
    labels: dict
    selector_labels: dict
    service_type: str
    ports: list[dict]
    force_namespace: str = None
    

class KubecostParameters(BaseModel):
    # https://docs.kubecost.com/apis/apis-overview/allocation
    aggregate: str = None
    accumulate: bool = True
    window: str = None
    step: str = None
    resolution: str = None

class ComputeUsageRequest(BaseModel):
    resources: List[str] = ["amd_com_gpu", "nvidia_com_gpu", "cpu", "memory"]
    resource_mapping: dict = {"amd_com_gpu": "gpus", "nvidia_com_gpu": "gpus", "memory": "ram"}
    node_names: List[str] = None
    namespaces: List[str] = None
    start_time: str
    end_time: str
    step_seconds: int = 300
    node_labels: dict = None
    normalize: bool = False

class NodeCostRequest(BaseModel):
    node_names: List[str] = None
    node_labels: dict = None
    kubecost_params: KubecostParameters
    aggregate_results: bool = False

class PodsWithStatusRequest(BaseModel):
    node_names: List[str] = None
    statuses: List[str]

class ServiceWithLabelRequest(BaseModel):
    label: str
    value: str = None
    types: list = None
    namespace: str = None
    

class NamespacesCostRequest(BaseModel):
    namespace_names: List[str]
    kubecost_params: KubecostParameters

class DeepsparseDeploymentRequest(BaseModel):
    namespace: str
    deployment_name: str
    deepsparse_model_id: str
    task: str
    num_cores: int
    ram_memory: str
    ephemeral_memory: str
    replicas: int
    
class DeepsparseDeploymentDeleteRequest(BaseModel):
    namespace: str
    deployment_name: str

class DeepsparseDeploymentListRequest(BaseModel):
    namespace: str
    
class NodesRequest(BaseModel):
    node_names: List[str] = None
    node_labels: dict = None
    schedulable: bool = True
    detailed: bool = False

class GenericDeploymentRequest(BaseModel):
    config: str
    force_namespace: str = None

class UserWorkspaceRequest(BaseModel):
    force_namespace: str = None
    user_id: str = None
    node_name: str = None
    quota: dict = None

class CustomObjectRequest(BaseModel):
    group: str
    api_version: str
    plural: str
    name: str = ""
    force_namespace: str = None

class CustomObjectDeploymentRequest(BaseModel):
    object: CustomObjectRequest
    body: str
    force_namespace: str = None


class DeleteLabelledResourcesRequest(BaseModel):
    label:str
    value:Optional[str] = None
    force_namespace: str = None

class GetJobsOverviewRequest(BaseModel):
    labels: List[str]
    force_namespace: str = None

class GetLabelledResourcesRequest(BaseModel):
    label:str
    value:Optional[str] = None
    force_namespace: str = None
    tail_lines: int = 100
    
class UserRequest(BaseModel):
    email: str
    password: str

class JobTemplateRequest(BaseModel):
    force_namespace: str = None
    template_values: dict = None
    template: str
    target_labels: dict[str, Union[str, List]] = None
    target_labels_ops: Literal["OR", "AND"] = "AND"
    replicas: int = 1
    random_suffix: bool = True

class CustomJobTemplateRequest(BaseModel):
    force_namespace: str = None
    template_values: dict = None
    default_values: str
    template: str
    target_labels: dict[str, Union[str, List]] = None
    target_labels_ops: Literal["OR", "AND"] = "AND"
    replicas: int = 1
    random_suffix: bool = True

class RayClusterRequest(BaseModel):
    force_namespace: str = None
    name: str
    manifest: str

class NodeLabelsRequest(BaseModel):
    """
    Request model for adding labels to a node.
    
    Attributes:
        node_name (str): Name of the node to update
        labels (Dict[str, str]): Dictionary of labels to add to the node
    """
    node_name: str
    labels: Dict[str, str]
     