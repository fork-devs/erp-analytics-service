from datetime import date
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_analytics_service, get_current_tenant_id
from app.services.analytics_service import (
    AnalyticsService,
    BranchDailySummaryResponse,
    BranchFinancialSnapshotItem,
    FleetHealthResponse,
    NetworkSummaryResponse,
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


@router.get(
    "/branches/{branch_id}/summary",
    response_model=BranchDailySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get branch executive daily KPI summary",
)
def get_branch_daily_summary(
    branch_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> BranchDailySummaryResponse:
    """Returns today's executive KPI summary for the specified branch strictly isolated to the requesting tenant."""
    return service.get_branch_summary(tenant_id=tenant_id, branch_id=branch_id)


@router.get(
    "/branches/{branch_id}/financial",
    response_model=List[BranchFinancialSnapshotItem],
    status_code=status.HTTP_200_OK,
    summary="Get branch historical financial snapshots",
)
def get_branch_financial(
    branch_id: UUID,
    startDate: Optional[date] = Query(None, alias="startDate", description="Start date filter (YYYY-MM-DD)"),
    endDate: Optional[date] = Query(None, alias="endDate", description="End date filter (YYYY-MM-DD)"),
    start_date: Optional[date] = Query(None, description="Start date filter alternative (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter alternative (YYYY-MM-DD)"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> List[BranchFinancialSnapshotItem]:
    """Returns chronological daily financial snapshots for charting."""
    s_date = startDate or start_date
    e_date = endDate or end_date
    try:
        return service.get_branch_financial(
            tenant_id=tenant_id,
            branch_id=branch_id,
            start_date=s_date,
            end_date=e_date,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )


@router.get(
    "/network/summary",
    response_model=NetworkSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get consolidated network multi-branch summary",
)
@router.get(
    "/multi-branch/overview",
    response_model=NetworkSummaryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_network_summary(
    tenant_id: UUID = Depends(get_current_tenant_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> NetworkSummaryResponse:
    """Returns consolidated network KPIs across all active branches in the requesting tenant."""
    return service.get_network_summary(tenant_id=tenant_id)

