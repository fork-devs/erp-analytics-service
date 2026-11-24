from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException, Header, Request, status

from app.core.security import (
    NIL_UUID,
    parse_non_nil_uuid,
    verify_access_token_and_extract_tenant,
    verify_access_token_claims,
)
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService


@dataclass(frozen=True)
class AuthenticatedUserContext:
    user_id: str
    tenant_id: UUID
    roles: set[str]


def get_analytics_repo(request: Request) -> AnalyticsRepository:
    """Dependency injecting AnalyticsRepository from application state."""
    repo = getattr(request.app.state, "analytics_repo", None)
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics repository is currently unavailable",
        )
    return repo


def get_analytics_service(request: Request) -> AnalyticsService:
    """Dependency injecting AnalyticsService."""
    repo = get_analytics_repo(request)
    return AnalyticsService(repository=repo)


def get_current_tenant_id(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID:
    """Verify Bearer JWT, extract tenant_id claim, and cross-check optional X-Tenant-ID header."""
    auth_header = authorization or request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer authentication token",
        )

    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
        )

    token_tenant_id = verify_access_token_and_extract_tenant(token)

    raw_header_tenant = x_tenant_id or request.headers.get("X-Tenant-ID")
    if raw_header_tenant and raw_header_tenant.strip():
        try:
            header_tenant_id = UUID(str(raw_header_tenant).strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Tenant-ID header: must be a valid UUID",
            )
        if header_tenant_id == NIL_UUID or header_tenant_id != token_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="X-Tenant-ID header does not match authenticated token tenant",
            )

    return token_tenant_id


def get_current_user_context(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> AuthenticatedUserContext:
    """Verify Bearer JWT and return user subject, tenant_id, and normalized roles."""
    auth_header = authorization or request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer authentication token",
        )
    token = auth_header[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
        )
    claims = verify_access_token_claims(token)
    tenant_id = parse_non_nil_uuid(claims.get("tenant_id"), "Token missing valid tenant_id claim")

    raw_header_tenant = x_tenant_id or request.headers.get("X-Tenant-ID")
    if raw_header_tenant and raw_header_tenant.strip():
        try:
            header_tenant_id = UUID(str(raw_header_tenant).strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Tenant-ID header: must be a valid UUID",
            )
        if header_tenant_id == NIL_UUID or header_tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="X-Tenant-ID header does not match authenticated token tenant",
            )

    raw_roles = claims.get("roles") or []
    roles: set[str] = set()
    if isinstance(raw_roles, list):
        roles.update(str(r).upper().removeprefix("ROLE_") for r in raw_roles if r)
    elif isinstance(raw_roles, str) and raw_roles.strip():
        roles.add(raw_roles.strip().upper().removeprefix("ROLE_"))
    single_role = claims.get("role")
    if isinstance(single_role, str) and single_role.strip():
        roles.add(single_role.strip().upper().removeprefix("ROLE_"))

    return AuthenticatedUserContext(
        user_id=str(claims.get("sub", "")),
        tenant_id=tenant_id,
        roles=roles,
    )
