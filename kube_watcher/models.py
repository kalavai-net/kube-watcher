from typing import List, Optional
from pydantic import BaseModel

class NodeStatusRequest(BaseModel):
    node_id: str = "carlosfm-desktop-2"
    start_time: str = "1h"
    end_time: str = "now"
    chunk_size: int = 1
    

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
    
class NodeLabelsRequest(BaseModel):
    node_names: List[str] = None

class GenericDeploymentRequest(BaseModel):
    config: str

class DeleteLabelledResourcesRequest(BaseModel):
    namespace:str
    label:str
    value:Optional[str] = None

class GetLabelledResourcesRequest(BaseModel):
    namespace:str
    label:str
    value:Optional[str] = None

class FlowDeploymentRequest(BaseModel):
    deployment_name: str
    namespace: str
    api_key: str = ""
    flow_id: str = ""
    flow_url: str = ""
    num_cores: int = 0.5
    ram_memory: str = "0.5Gi"
    

class AgentBuilderDeploymentRequest(BaseModel):
    deployment_name: str
    namespace: str
    username: str
    password: str
    num_cores: int = 1
    replicas: int = 1
    ram_memory: str = "1.5Gi"
    storage_memory: str = "0.5Gi"
    
class UserRequest(BaseModel):
    email: str
    password: str
