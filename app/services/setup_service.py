"""Service for setting up default roles and permissions from configuration files."""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.role import Role
from app.commands.setup.setup_command import SetupCommand
from tessera_sdk.events.nats_router import NatsEventPublisher  # type: ignore


class SetupService:
    """
    Service wrapper for the setup command.
    This service delegates to SetupCommand to maintain backward compatibility.
    """

    def __init__(
        self,
        db: Session,
        nats_publisher: Optional[NatsEventPublisher] = None,
    ):
        """
        Initialize the setup service.

        Args:
            db: Database session
            nats_publisher: Optional NATS event publisher
        """
        self.db = db
        self.nats_publisher = nats_publisher

    def import_roles_from_yaml(
        self, yaml_file_path: Optional[str] = None
    ) -> List[Role]:
        """
        Import roles and permissions from a YAML configuration file.

        This method delegates to SetupCommand.execute().

        Args:
            yaml_file_path: Path to the YAML file. If None, uses default_roles.yaml
                from app/config directory.

        Returns:
            List[Role]: The created roles

        Raises:
            ValueError: If super_user_email is not configured in settings
            FileNotFoundError: If the YAML file doesn't exist
            ValueError: If the YAML file is invalid or roles already exist
        """
        command = SetupCommand(self.db, self.nats_publisher)
        return command.execute(yaml_file_path)
