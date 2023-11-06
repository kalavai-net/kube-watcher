from typing import List
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


class ValidateUserRequest(BaseModel):
    username: str
    password: str

class LinkNodeUserRequest(BaseModel):
    user: ValidateUserRequest
    node_name: str
    os: str
    
class NodeLabelsRequest(BaseModel):
    node_names: List[str] = None

class RayClusterRequest(BaseModel):
    namespace: str
    