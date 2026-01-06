from pydantic import BaseModel, Field
from typing import Optional


class BindingRequest(BaseModel):
    """Request model for role bindings."""

    user_id: str = Field(..., description="The ID of the user")
    domain: Optional[str] = Field(None, description="The domain/tenant for the role")
    domain_metadata: Optional[dict] = Field(
        None, description="The metadata for the domain"
    )
    resource: Optional[str] = Field(
        None, description="The resource the role applies to"
    )
