from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.config import get_settings
from app.services.user_service import UserService
from app.services.role_definition_service import role_definition_service
from app.services.casbin_service import casbin_service
from app.core.logging_config import get_logger
from pydantic import BaseModel

router = APIRouter(prefix="/setup", tags=["setup"])
logger = get_logger()


class SetupResponse(BaseModel):
    """Response model for setup endpoint."""

    success: bool
    message: str
    super_user_email: Optional[str] = None
    user_id: Optional[str] = None
    role_assigned: Optional[str] = None


class SystemStatusResponse(BaseModel):
    """Response model for system status endpoint."""

    setup_required: bool
    message: str


@router.get("/system-status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """
    Check if the system administrator has been set up.

    Returns setup_required=true if no system admin users exist,
    setup_required=false if at least one system admin user exists.
    """
    try:
        # Check for system admin users in the global domain (*)
        system_admin_users = casbin_service.get_users_for_role(
            "system_admin", domain="*"
        )

        if system_admin_users:
            logger.info(f"System admin users found: {len(system_admin_users)}")
            return SystemStatusResponse(
                setup_required=False,
                message=f"System administrator is already set up. Found {len(system_admin_users)} system admin user(s).",
            )
        else:
            logger.info("No system admin users found. Setup is required.")
            return SystemStatusResponse(
                setup_required=True,
                message="System administrator has not been set up. Call POST /setup to initialize the system admin.",
            )

    except Exception as e:
        logger.error(f"Error checking system status: {e}")
        # In case of error, assume setup is required to be safe
        return SystemStatusResponse(
            setup_required=True,
            message=f"Error checking system status: {str(e)}. Setup may be required.",
        )


@router.post("", response_model=SetupResponse)
async def setup_super_user(db: Session = Depends(get_db)) -> SetupResponse:
    """
    Set up a system administrator role and assign it to the user specified by SUPER_USER_EMAIL.
    """
    settings = get_settings()
    if not settings.super_user_email:
        raise HTTPException(
            status_code=400,
            detail="SUPER_USER_EMAIL environment variable is not set. Cannot proceed with system admin setup.",
        )
    system_admin_email = settings.super_user_email
    user_service = UserService(db)
    user = user_service.get_user_by_email(system_admin_email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"No user found with email: {system_admin_email}. Please ensure the user exists in the database before running setup.",
        )
    try:
        logger.info(f"Defining system admin role for user: {system_admin_email}")
        role_defined = role_definition_service.define_system_admin_role(domain="*")
        if not role_defined:
            raise HTTPException(
                status_code=500,
                detail="Failed to define system admin role. Check logs for details.",
            )
        logger.info(f"Assigning system admin role to user: {user.id}")
        role_assigned = casbin_service.assign_role(
            user_id=str(user.id), role="system_admin", domain="*"
        )
        if not role_assigned:
            raise HTTPException(
                status_code=500,
                detail="Failed to assign system admin role to user. Check logs for details.",
            )
        logger.info(
            f"System admin setup completed successfully: email={system_admin_email}, "
            f"user_id={user.id}, role=system_admin"
        )
        return SetupResponse(
            success=True,
            message=f"System admin setup completed successfully. User {system_admin_email} now has system administrator privileges.",
            super_user_email=system_admin_email,
            user_id=str(user.id),
            role_assigned="system_admin",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during system admin setup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during system admin setup: {str(e)}",
        )
