from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.services.casbin_service import CasbinService
from app.models.user import User
from app.core.logging_config import get_logger
from typing import List, Optional
import re

GLOBAL_DOMAIN = "*"


# 2. RBAC Middleware
class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, skip_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.casbin_service = CasbinService()
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
        assert isinstance(user, User)

        resource = self._extract_resource(path)
        action = self._get_action(request)

        self.logger.info("RBAC Middleware:")
        self.logger.info(f"Path: {path}")
        self.logger.info(f"Resource: {resource}")
        self.logger.info(f"Method: {request.method}")
        self.logger.info(f"Action: {action}")
        self.logger.info(f"User: {user.email}")
        self.logger.info(f"User ID: {user.id}")
        self.logger.info("--------------------------------")

        allowed = self.casbin_service.authorize(
            user_id=str(user.id),
            resource=resource,
            action=action,
            domain=GLOBAL_DOMAIN,
        )

        if not allowed:
            self.logger.info("RBAC Middleware: Unauthorized response")
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={"error": "Forbidden"},
            )

        self.logger.info("RBAC Middleware: Request allowed")
        return await call_next(request)

    def _extract_resource(self, path: str) -> str:
        segments = [s for s in path.split("/") if s]
        if not segments:
            return "root"
        return self._singularize(segments[0])

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
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "delete",
        }.get(method, "read")
