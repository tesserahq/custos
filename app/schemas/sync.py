from pydantic import BaseModel, Field
from typing import Optional, List


class CasbinBinding(BaseModel):
    user_id: str
    role_identifier: str
    domain: Optional[str] = None


class SyncRequest(BaseModel):
    user_id: str = Field(..., description="The ID of the user")
    domain: Optional[str] = Field(
        None, description="Optional domain to narrow the operation"
    )


class SyncCheckRequest(SyncRequest):
    pass


class SyncCheckResponse(BaseModel):
    in_sync: bool
    orphan_casbin_bindings: List[CasbinBinding]
    missing_casbin_bindings: List[CasbinBinding]


class SyncFixRequest(SyncRequest):
    pass


class SyncFixResponse(BaseModel):
    removed_from_casbin: List[CasbinBinding]
    added_to_casbin: List[CasbinBinding]
    events_published: int
