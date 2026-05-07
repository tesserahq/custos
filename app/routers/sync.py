from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.sync import (
    SyncCheckRequest,
    SyncCheckResponse,
    SyncFixRequest,
    SyncFixResponse,
)
from app.commands.sync.check_membership_sync_command import CheckMembershipSyncCommand
from app.commands.sync.fix_membership_sync_command import FixMembershipSyncCommand

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post("/check", response_model=SyncCheckResponse)
def check_sync(
    request: SyncCheckRequest,
    db: Session = Depends(get_db),
) -> SyncCheckResponse:
    """
    Compare DB memberships against Casbin role bindings for a user.

    Returns orphan Casbin bindings (in Casbin but not in DB) and missing
    Casbin bindings (in DB but not in Casbin). Safe to call repeatedly —
    no state is mutated.
    """
    command = CheckMembershipSyncCommand(db)
    return command.execute(user_id=request.user_id, domain=request.domain)


@router.post("/fix", response_model=SyncFixResponse)
def fix_sync(
    request: SyncFixRequest,
    db: Session = Depends(get_db),
) -> SyncFixResponse:
    """
    Reconcile Casbin role bindings to match DB memberships (DB is source of truth).

    Removes orphan Casbin bindings and adds missing ones. Publishes
    membership.created / membership.deleted NATS events for each change.
    """
    command = FixMembershipSyncCommand(db)
    return command.execute(user_id=request.user_id, domain=request.domain)
