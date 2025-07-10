from typing import Optional, List
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
    super_user_emails: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
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
    Set up a system administrator role and assign it to the users specified by SUPER_USER_EMAIL.
    Supports comma-separated list of emails.
    """
    settings = get_settings()
    super_user_emails = settings.get_super_user_emails()

    if not super_user_emails:
        raise HTTPException(
            status_code=400,
            detail="SUPER_USER_EMAIL environment variable is not set or contains no valid emails. Cannot proceed with system admin setup.",
        )

    user_service = UserService(db)
    successful_users = []
    failed_emails = []

    try:
        # Define system admin role once for all users
        logger.info("Defining system admin role")
        role_defined = role_definition_service.define_system_admin_role(domain="*")
        if not role_defined:
            raise HTTPException(
                status_code=500,
                detail="Failed to define system admin role. Check logs for details.",
            )

        # Process each email in the list
        for email in super_user_emails:
            user = user_service.get_user_by_email(email)
            if not user:
                failed_emails.append(email)
                logger.warning(f"No user found with email: {email}")
                continue

            logger.info(f"Assigning system admin role to user: {user.id} ({email})")
            role_assigned = casbin_service.assign_role(
                user_id=str(user.id), role="system_admin", domain="*"
            )
            if not role_assigned:
                failed_emails.append(email)
                logger.error(f"Failed to assign system admin role to user: {email}")
                continue

            successful_users.append({"email": email, "user_id": str(user.id)})
            logger.info(f"Successfully assigned system admin role to user: {email}")

        # Check if any users were successfully set up
        if not successful_users:
            raise HTTPException(
                status_code=404,
                detail=f"No users found with the provided emails: {', '.join(super_user_emails)}. Please ensure the users exist in the database before running setup.",
            )

        # Prepare response message
        if failed_emails:
            message = (
                f"System admin setup completed with partial success. "
                f"Successfully set up {len(successful_users)} user(s): {', '.join([u['email'] for u in successful_users])}. "
                f"Failed to set up {len(failed_emails)} user(s): {', '.join(failed_emails)}."
            )
        else:
            message = (
                f"System admin setup completed successfully. "
                f"Users {', '.join([u['email'] for u in successful_users])} now have system administrator privileges."
            )

        logger.info(
            f"System admin setup completed: {len(successful_users)} successful, {len(failed_emails)} failed"
        )

        return SetupResponse(
            success=True,
            message=message,
            super_user_emails=[u["email"] for u in successful_users],
            user_ids=[u["user_id"] for u in successful_users],
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
