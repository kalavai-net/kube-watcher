from typing import List, Optional, Dict
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


class RayDeploymentRequest(BaseModel):
    namespace: str
    deployment_name: str
    ray_model_id: str
    num_cpus: int
    num_gpus: int
    num_replicas: int
    tokenizer_id: Optional[str] = None
    tokenizer_args: Optional[Dict] = None
    tokenizing_args: Optional[Dict] = None
    generation_args: Optional[Dict] = None
    ray_model_args: Optional[Dict] = None


class RayDeploymentDeleteRequest(BaseModel):
    namespace: Optional[str] = None
    deployment_name: str


class RayDeploymentListRequest(BaseModel):
    namespace: Optional[str] = None


class NodeLabelsRequest(BaseModel):
    node_names: List[str] = None


class RayDeploymentControlRequest(BaseModel):
    deployment_name: str
    namespace: str
    num_replicas: int = 1  # Only used for resuming to specify the number of replicas


# GENERIC DEPLOYMENTS


class GenericDeploymentRequest(BaseModel):
    config: str
    crd: bool = False  # should we deploy this as a crd
