from typing import List
from pydantic import BaseModel

class NodeStatusRequest(BaseModel):
    node_id: str = "carlosfm-desktop-2"
    start_time: str = "1h"
    end_time: str = "now"
    chunk_size: int = 1


class ValidateUserRequest(BaseModel):
    username: str
    password: str

class LinkNodeUserRequest(BaseModel):
    user: ValidateUserRequest
    node_name: str
    
class NodeLabelsRequest(BaseModel):
    node_names: List[str] = None
