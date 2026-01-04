"""System router for setup and maintenance endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from app.db import get_db
from app.schemas.system import SetupRequest, SetupResponse
from app.commands.setup.setup_command import SetupCommand
from app.schemas.role import Role
from app.core.logging_config import get_logger

router = APIRouter(prefix="/system", tags=["System"])
logger = get_logger()


@router.post("/setup", response_model=SetupResponse, status_code=201)
def setup_system(
    request: Optional[SetupRequest] = Body(None), db: Session = Depends(get_db)
) -> SetupResponse:
    """
    Import roles and permissions from JSON configuration file.

    This endpoint reads the default_roles.json file (or a custom path if provided)
    and imports all defined roles and permissions into the system.

    Args:
        request: Optional request body with json_file_path. If None or empty, uses default path.

    Returns:
        SetupResponse with details about the created roles.
    """
    try:
        # Get the JSON file path from request, or None to use default
        json_file_path = (
            request.json_file_path if request and request.json_file_path else None
        )

        command = SetupCommand(db, nats_publisher=None)
        created_roles = command.execute(json_file_path)

        logger.info(f"System setup completed: {len(created_roles)} roles created")

        return SetupResponse(
            success=True,
            roles_created=len(created_roles),
            roles=[
                Role.model_validate(role, from_attributes=True)
                for role in created_roles
            ],
            message=f"Successfully imported {len(created_roles)} role(s) from configuration",
        )

    except FileNotFoundError as e:
        logger.error(f"System setup failed: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"System setup failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"System setup failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to setup system")
