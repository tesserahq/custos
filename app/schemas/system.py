"""Schemas for system setup endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List
from app.schemas.role import Role


class SetupRequest(BaseModel):
    """Request model for system setup endpoint."""

    json_file_path: Optional[str] = Field(
        None,
        description="Optional path to JSON file. If not provided, uses default_roles.json",
    )


class SetupResponse(BaseModel):
    """Response model for system setup endpoint."""

    success: bool = Field(..., description="Whether the setup was successful")
    roles_created: int = Field(..., description="Number of roles created")
    roles: List[Role] = Field(..., description="List of created roles")
    message: str = Field(..., description="Success or error message")
