from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.health import router as health_router
from app.core.config import get_settings
from app.core.lifespan import lifespan
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.LOG_LEVEL)

app = FastAPI(
    title="DriveOS - ERP Analytics Service",
    description="Multi-tenant OLAP analytical reporting engine and KPI aggregator powered by ClickHouse and Kafka",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers (RFC 9457)
register_error_handlers(app)

# Include Routers
app.include_router(health_router)
app.include_router(analytics_router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.ENVIRONMENT != "production" else "disabled",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
