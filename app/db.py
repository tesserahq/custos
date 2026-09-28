"""
Database setup and the application's transaction boundary.

One execution (HTTP request, middleware lookup, background job) gets one
SQLAlchemy ``Session``. The session commits when the execution succeeds, rolls
back when an exception escapes, and closes. Repositories and commands never
end the transaction. The mechanics come from tessera_sdk
(docs/managed-transactions.md in tessera-sdk-py); this module wires them to
Custos' settings and re-exports them under the names the app imports.
"""

from app.config import get_settings
from tessera_sdk.infra import current_session, on_commit, savepoint
from tessera_sdk.infra.database import DatabaseManager
from tessera_sdk.server.dependencies import create_db_dependency
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm import with_loader_criteria

__all__ = [
    "Base",
    "DbSession",
    "SessionLocal",
    "current_session",
    "db_manager",
    "engine",
    "get_db",
    "on_commit",
    "savepoint",
    "session_scope",
]

Base = declarative_base()


@event.listens_for(Session, "do_orm_execute")
def _add_soft_delete_criteria(execute_state):
    """
    Automatically filter out soft-deleted records from all queries.

    This listener is automatically skipped during Alembic migrations to avoid
    interfering with migration operations.
    """
    # Skip soft delete filtering during Alembic migrations
    # Check execution option first (set in alembic/env.py)
    is_alembic_context = execute_state.execution_options.get("alembic_context", False)

    # Fallback: check if we're in an Alembic context by inspecting the call stack
    # This handles cases where execution options might not propagate
    if not is_alembic_context:
        try:
            import inspect

            # Check if alembic is in the call stack
            stack = inspect.stack()
            is_alembic_context = any(
                "alembic" in frame.filename.lower() for frame in stack
            )
        except Exception:
            # If we can't inspect the stack, continue with normal filtering
            pass

    if is_alembic_context:
        return  # Skip soft delete filtering during migrations

    from app.models.user import User
    from app.models.role import Role
    from app.models.permission import Permission

    skip_filter = execute_state.execution_options.get("skip_soft_delete_filter", False)
    if execute_state.is_select and not skip_filter:
        # Apply soft delete filter to all models that use SoftDeleteMixin
        # with_loader_criteria requires mapped entity classes, not mixins
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                User,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            ),
            with_loader_criteria(
                Role,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            ),
            with_loader_criteria(
                Permission,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            ),
        )


# Initialize database manager
settings = get_settings()
db_manager = DatabaseManager(
    database_url=settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_use_lifo=True,
    application_name=settings.db_app_name,
    autoflush=True,
)

engine = db_manager.engine
SessionLocal = db_manager.SessionLocal

# One managed session per execution: routes declare `db: DbSession`; the
# authentication middleware and other entry points use
# `with session_scope() as db:`.
get_db, DbSession = create_db_dependency(db_manager)
session_scope = db_manager.session_scope
