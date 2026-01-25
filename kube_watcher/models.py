from typing import List, Optional, Dict, Literal, Union
from pydantic import BaseModel, Field
from enum import Enum

# This are off-the-shelf supported templates
class JobTemplate(Enum):
    custom = 0
    vllm = 1
    #aphrodite = 2
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
    inference = 19
    pool = 20
    #flexible = 99

class NodeStatusRequest(BaseModel):
    node_names: List[str] = None
    node_labels: dict = None
    start_time: str = "1h"
    end_time: str = "now"
    step: str = "1m"
    resources: List[str] = ["amd_com_gpu", "nvidia_com_gpu"]
    aggregate_results: bool = False

class StorageClaimRequest(BaseModel):
    name: str
    labels: dict
    access_modes: list
    storage_class_name: str
    storage_size: int
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")

class StorageRequest(BaseModel):
    names: list = None

class ServiceRequest(BaseModel):
    name: str
    labels: dict
    selector_labels: dict
    service_type: str
    ports: list[dict]
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")
    

class KubecostParameters(BaseModel):
    # https://docs.kubecost.com/apis/apis-overview/allocation
    aggregate: Optional[Union[str, None]] = Field(None, description="Whether to aggregate samples into a single result")
    accumulate: bool = True
    window: Optional[Union[str, None]] = Field(None, description="What window to sample")
    step: Optional[Union[str, None]] = Field(None, description="Time step for sampling")
    resolution: Optional[Union[str, None]] = Field(None, description="Resolution of the sampling")

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
    value: Optional[Union[str, None]] = Field(None, description="Optional label value to filter services")
    types: list = None
    namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace to filter services")


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

class HelmRepo(BaseModel):
    name: str
    url: Optional[Union[str, None]] = Field(None, description="Optional repo URL")

class GenericDeploymentRequest(BaseModel):
    config: str
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")

class UserWorkspaceRequest(BaseModel):
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")
    user_id: str = None
    node_name: str = None
    quota: dict = None

class CustomObjectRequest(BaseModel):
    group: str
    api_version: str
    plural: str
    name: str = ""
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")

class CustomObjectDeploymentRequest(BaseModel):
    object: CustomObjectRequest
    body: str
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")


class DeleteLabelledResourcesRequest(BaseModel):
    label: str
    value: Optional[Union[str, None]] = Field(None, description="Optional value to match label")
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")

class GetJobsOverviewRequest(BaseModel):
    labels: List[str]
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")

class GetLabelledResourcesRequest(BaseModel):
    label: str
    value: Optional[Union[str, None]] = Field(None, description="Optional value to match the label")
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")
    tail_lines: int = 100
    
class UserRequest(BaseModel):
    email: str
    password: str

class TemplateDeploymentRequest(BaseModel):
    name: str
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")
    template_values: dict = None
    template_chart: str
    template_version: Optional[Union[str, None]] = Field(None, description="Optional template chart version to deploy")
    template_repo: Optional[str] = Field("kalavai-templates", description="Optional template repo to find the chart in")
    target_labels: Optional[Union[dict[str, Union[str, List]], None]] = None
    target_labels_ops: Literal["OR", "AND"] = "AND"
    replicas: int = 1
    priority: Literal["kalavai-system-priority", "user-high-priority", "user-spot-priority", "test-low-priority", "test-high-priority"] = "user-spot-priority"
    is_update: Optional[bool] = Field(False, description="If True, update existing deployment")

class TemplateDeleteRequest(BaseModel):
    name: str
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")


class JobTemplateRequest(BaseModel):
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")
    template_values: dict = None
    template: str
    target_labels: Optional[Union[dict[str, Union[str, List]], None]] = None
    target_labels_ops: Literal["OR", "AND"] = "AND"
    replicas: int = 1
    random_suffix: bool = True
    priority: Literal["kalavai-system-priority", "user-high-priority", "user-spot-priority", "test-low-priority", "test-high-priority"] = "user-spot-priority"

class CustomJobTemplateRequest(BaseModel):
    force_namespace: Optional[Union[str, None]] = Field(None, description="Optional namespace override")
    template_values: dict = None
    default_values: str
    template: str
    target_labels: Optional[Union[dict[str, Union[str, List]], None]] = None
    target_labels_ops: Literal["OR", "AND"] = "AND"
    replicas: int = 1
    random_suffix: bool = True
    priority: Literal["kalavai-system-priority", "user-high-priority", "user-spot-priority", "test-low-priority", "test-high-priority"] = "user-spot-priority"


class NodeLabelsRequest(BaseModel):
    """
    Request model for adding labels to a node.
    
    Attributes:
        node_name (str): Name of the node to update
        labels (Dict[str, str]): Dictionary of labels to add to the node
    """
    node_name: str
    labels: Dict[str, str]
     