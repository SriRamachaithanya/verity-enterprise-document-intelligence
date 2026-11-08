import secrets
from enum import Enum
from typing import Annotated

from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from src.api.config import get_api_config


class UserRole(str, Enum):
    ADMIN = "admin"
    AUDITOR = "auditor"
    USER = "user"


class AuthenticatedUser(BaseModel):
    user_id: str
    role: UserRole
    is_authenticated: bool = True


api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    x_api_key: Annotated[str | None, Security(api_key_header_scheme)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    """
    Authenticate user via X-API-Key header or Authorization: Bearer <token>.
    Resolves assigned RBAC role (admin, auditor, user).
    """
    config = get_api_config()

    # Allow bypassing authentication in dev/test if explicitly configured
    if config.auth_disabled:
        return AuthenticatedUser(user_id="dev-bypass-user", role=UserRole.ADMIN)

    raw_key = None
    if x_api_key:
        raw_key = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        raw_key = authorization[7:].strip()

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication credential. Provide 'X-API-Key' or 'Authorization: Bearer <key>' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate against configured role keys using constant-time comparison to prevent timing attacks
    if secrets.compare_digest(raw_key, config.admin_api_key):
        return AuthenticatedUser(user_id="admin-user", role=UserRole.ADMIN)
    elif secrets.compare_digest(raw_key, config.auditor_api_key):
        return AuthenticatedUser(user_id="auditor-user", role=UserRole.AUDITOR)
    elif secrets.compare_digest(raw_key, config.user_api_key):
        return AuthenticatedUser(user_id="standard-user", role=UserRole.USER)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication key provided.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def require_roles(allowed_roles: list[UserRole]):
    """Factory dependency enforcing RBAC roles."""

    def _role_checker(
        current_user: Annotated[AuthenticatedUser, Security(get_current_user)],
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role in {[r.value for r in allowed_roles]}, but user has role '{current_user.role.value}'.",
            )
        return current_user

    return _role_checker


# Role dependencies
require_admin = require_roles([UserRole.ADMIN])
require_auditor = require_roles([UserRole.ADMIN, UserRole.AUDITOR])
require_user = require_roles([UserRole.ADMIN, UserRole.AUDITOR, UserRole.USER])
