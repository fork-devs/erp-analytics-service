from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_analytics_service, get_current_tenant_id
from app.services.analytics_service import (
    AnalyticsService,
    FleetHealthResponse,
    RevenueTrendResponse,
    SummaryResponse,
    WorkOrderPerformanceResponse,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get(
    "/summary",
    response_model=SummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workshop executive KPI summary",
)
def get_workshop_summary(
    tenant_id: UUID = Depends(get_current_tenant_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> SummaryResponse:
    """Returns high-level workshop KPI summary strictly isolated to the requesting tenant."""
    return service.get_summary(tenant_id=tenant_id)


@router.get(
    "/revenue/trend",
    response_model=RevenueTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get revenue and gross margin trends",
)
def get_revenue_trend(
    interval: str = Query("monthly", pattern="^(monthly|weekly)$", description="Aggregation bucket: monthly or weekly"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> RevenueTrendResponse:
    """Returns time-series revenue and gross margin calculations."""
    return service.get_revenue_trend(
        tenant_id=tenant_id,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/work-orders/performance",
    response_model=WorkOrderPerformanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get work order turnaround and technician metrics",
)
def get_work_order_performance(
    tenant_id: UUID = Depends(get_current_tenant_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> WorkOrderPerformanceResponse:
    """Returns cycle times, lead times, and individual technician task completions."""
    return service.get_work_order_performance(tenant_id=tenant_id)


@router.get(
    "/fleet/health-overview",
    response_model=FleetHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get fleet health status and DTC breakdown",
)
def get_fleet_health_overview(
    tenant_id: UUID = Depends(get_current_tenant_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> FleetHealthResponse:
    """Returns overall vehicle fleet health index and diagnostic trouble code frequency."""
    return service.get_fleet_health(tenant_id=tenant_id)
