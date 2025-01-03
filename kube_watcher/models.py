from typing import List, Optional
from pydantic import BaseModel

class NodeStatusRequest(BaseModel):
    node_id: str = "carlosfm-desktop-2"
    start_time: str = "1h"
    end_time: str = "now"
    chunk_size: int = 1

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


class NodeCostRequest(BaseModel):
    node_names: List[str]
    kubecost_params: KubecostParameters

class PodsWithStatusRequest(BaseModel):
    node_names: List[str] = None
    statuses: List[str]

class ServiceWithLabelRequest(BaseModel):
    label: str
    value: str
    types: list = ["NodePort"]
    

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
    schedulable: bool = True

class GenericDeploymentRequest(BaseModel):
    config: str
    force_namespace: str = None

class CustomObjectRequest(BaseModel):
    group: str
    api_version: str
    plural: str
    name: str = ""

class CustomObjectDeploymentRequest(BaseModel):
    object: CustomObjectRequest
    body: str
    force_namespace: str = None


class DeleteLabelledResourcesRequest(BaseModel):
    label:str
    value:Optional[str] = None
    force_namespace: str = None

class GetLabelledResourcesRequest(BaseModel):
    label:str
    value:Optional[str] = None
    
class UserRequest(BaseModel):
    email: str
    password: str
