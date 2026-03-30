from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.repositories.casbin_repository import get_casbin_repository
from app.models.user import User
from app.core.logging_config import get_logger
from typing import List, Optional
import re
from app.repositories.casbin_repository import GLOBAL_DOMAIN

PREFIX = "custos"


# 2. RBAC Middleware
class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, skip_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.casbin_repository = get_casbin_repository()
        self.logger = get_logger()
        self.skip_paths = skip_paths or []

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip RBAC for paths in the skip list
        if path in self.skip_paths:
            self.logger.debug(
                f"RBAC Middleware: Skipping authorization for path: {path}"
            )
            return await call_next(request)

        # Allow OPTIONS requests
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        # Authentication must already have populated request.state.user
        if not hasattr(request.state, "user") or request.state.user is None:
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"error": "Unauthenticated"},
            )

        user = request.state.user

        resource = self._extract_resource(path)
        action = self._get_action(request)

        allowed = self.casbin_repository.authorize(
            user_id=str(user.id),
            resource=f"{PREFIX}.{resource}",
            action=action,
            domain=GLOBAL_DOMAIN,
        )

        self.logger.info(
            "RBAC Middleware authorize check",
            extra={
                "path": path,
                "resource": resource,
                "method": request.method,
                "action": action,
                "user": user.email,
                "user_id": user.id,
                "allowed": allowed,
            },
        )

        if not allowed:
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={"error": "Forbidden"},
            )

        return await call_next(request)

    def _extract_resource(self, path: str) -> str:
        """
        Extracts and normalizes the resource name from a URL path.
        Handles:
            - Singularizing resource names
            - Converting hyphens to underscores (e.g., permission-check -> permission_check)
            - Detecting "batch" and ID segments
        """

        def normalize(segment: str) -> str:
            if not segment:
                return segment
            # Convert hyphens to underscores
            segment = segment.replace("-", "_")
            return self._singularize(segment)

        segments = [s for s in path.split("/") if s]
        if not segments:
            return "root"

        # If the path ends with "batch", use the parent resource (e.g., /roles/batch -> role)
        if segments[-1] == "batch" and len(segments) > 1:
            return normalize(segments[-2])

        # Check if the last segment looks like an ID (UUID etc)
        last_segment = segments[-1]
        if self._looks_like_id(last_segment) and len(segments) > 1:
            return normalize(segments[-2])
        else:
            return normalize(last_segment)

    def _looks_like_id(self, segment: str) -> bool:
        """
        Check if a path segment looks like an ID (UUID format).
        UUIDs can be in formats like:
        - xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (with dashes)
        - xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (without dashes, 32 hex chars)
        """
        if not segment:
            return False

        # UUID with dashes: 8-4-4-4-12 hex characters
        uuid_with_dashes = re.match(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            segment,
            re.IGNORECASE,
        )
        if uuid_with_dashes:
            return True

        # UUID without dashes: 32 hex characters
        uuid_without_dashes = re.match(r"^[0-9a-f]{32}$", segment, re.IGNORECASE)
        if uuid_without_dashes:
            return True

        return False

    def _singularize(self, word: str) -> str:
        if not word:
            return word

        word_lower = word.lower()
        irregulars = {
            "people": "person",
            "children": "child",
            "men": "man",
            "women": "woman",
            "feet": "foot",
            "teeth": "tooth",
            "mice": "mouse",
        }

        if word_lower in irregulars:
            return irregulars[word_lower]

        if word_lower.endswith("ies") and len(word_lower) > 3:
            return word_lower[:-3] + "y"

        if word_lower.endswith("es") and not word_lower.endswith("ies"):
            without_es = word_lower[:-2]
            if word_lower[-4:-2] in ("ch", "sh") or word_lower[-3] in ("s", "x", "z"):
                return without_es
            if word_lower.endswith("ses") and len(word_lower) > 4:
                return word_lower[:-2]

        if word_lower.endswith("s") and not word_lower.endswith(("ss", "us", "is")):
            return word_lower[:-1]

        return word_lower

    def _get_action(self, request: Request) -> str:
        method = request.method.upper()
        return {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }.get(method, "read")
