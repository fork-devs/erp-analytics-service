from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def liveness() -> dict:
    """Kubernetes liveness probe returning 200 OK if service process is running."""
    return {"status": "alive"}


@router.get("/readyz")
async def readiness(request: Request) -> JSONResponse:
    """Kubernetes readiness probe verifying active connectivity to ClickHouse."""
    manager = getattr(request.app.state, "clickhouse_manager", None)
    if manager is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "clickhouse": "not_initialized"},
        )

    try:
        client = manager.get_client()
        result = client.command("SELECT 1")
        if int(result) == 1:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "ready", "clickhouse": "connected"},
            )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "clickhouse": "disconnected", "error": str(e)},
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "degraded", "clickhouse": "unexpected_response"},
    )
