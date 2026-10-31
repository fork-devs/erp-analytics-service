from uuid import UUID
from fastapi import HTTPException, Header, Request, status

from app.core.config import get_settings
from app.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics_service import AnalyticsService


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
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID:
    """Extracts and validates tenant UUID from header or development environment fallback."""
    settings = get_settings()

    raw_tenant = x_tenant_id or request.headers.get("X-Tenant-ID")

    if not raw_tenant and settings.ENVIRONMENT == "development":
        # Fallback for dev/testing when gateway headers are omitted
        raw_tenant = "00000000-0000-0000-0000-000000000001"

    if not raw_tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-Tenant-ID authentication header",
        )

    try:
        return UUID(str(raw_tenant).strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header: must be a valid UUID",
        )
