from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.utils.auth import verify_token_dependency, verify_service_account_token


class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/health", "/openapi.json", "/docs"]:
            return await call_next(request)

        # Check for service account token first (X-Service-Token header)
        service_token = request.headers.get("X-Service-Token")
        if service_token:
            try:
                verify_service_account_token(request, service_token)
                return await call_next(request)
            except HTTPException as e:
                if e.status_code == status.HTTP_401_UNAUTHORIZED:
                    return JSONResponse(
                        status_code=401, content={"error": "Invalid service token"}
                    )
                elif e.status_code == status.HTTP_403_FORBIDDEN:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Service account access denied"},
                    )
                elif e.status_code == status.HTTP_410_GONE:
                    return JSONResponse(
                        status_code=410,
                        content={"error": "Service account expired or inactive"},
                    )

        # Fall back to JWT authentication (Authorization header)
        authorization: str = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401, content={"error": "Missing or invalid token"}
            )

        token = authorization[len("Bearer ") :]

        try:
            # Now manually pass the raw token
            verify_token_dependency(request, token)
        except HTTPException as e:
            if e.status_code == status.HTTP_401_UNAUTHORIZED:
                return JSONResponse(status_code=401, content={"error": "Invalid token"})
            elif e.status_code == status.HTTP_403_FORBIDDEN:
                return JSONResponse(status_code=403, content={"error": "Forbidden"})

        return await call_next(request)
