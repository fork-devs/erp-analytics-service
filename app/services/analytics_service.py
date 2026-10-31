from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.repositories.analytics_repository import AnalyticsRepository


# -------------------------------------------------------------
# Domain / DTO Models
# -------------------------------------------------------------
class SummaryResponse(BaseModel):
    tenant_id: UUID
    total_revenue: float = Field(..., description="Cumulative revenue from issued invoices")
    active_work_orders: int = Field(..., description="Count of currently active work orders")
    completed_work_orders: int = Field(..., description="Count of completed work orders")
    total_alerts: int = Field(..., description="Count of telemetry anomaly alerts")


class RevenueTrendItem(BaseModel):
    period: str
    gross_revenue: float
    parts_cost: float
    labor_cost: float
    gross_margin_percentage: float


class RevenueTrendResponse(BaseModel):
    tenant_id: UUID
    interval: str
    trends: List[RevenueTrendItem]


class TechnicianPerformance(BaseModel):
    technician_id: str
    jobs_completed: int
    avg_cycle_time_hours: float


class WorkOrderPerformanceResponse(BaseModel):
    tenant_id: UUID
    average_cycle_time_hours: float
    average_lead_time_hours: float
    on_time_percentage: float
    technicians: List[TechnicianPerformance]


class DtcCodeSummary(BaseModel):
    dtc_code: str
    occurrences: int


class FleetHealthResponse(BaseModel):
    tenant_id: UUID
    total_vehicles_monitored: int
    critical_alerts: int
    warning_alerts: int
    fleet_health_score: float = Field(..., ge=0.0, le=100.0)
    top_dtc_codes: List[DtcCodeSummary]


# -------------------------------------------------------------
# Analytics Service
# -------------------------------------------------------------
class AnalyticsService:
    """Service layer calculating and formatting analytics summaries for REST endpoints."""

    def __init__(self, repository: AnalyticsRepository):
        self._repo = repository

    def get_summary(self, tenant_id: UUID) -> SummaryResponse:
        data = self._repo.get_workshop_summary(tenant_id)
        return SummaryResponse(
            tenant_id=UUID(data["tenant_id"]),
            total_revenue=data["total_revenue"],
            active_work_orders=data["active_work_orders"],
            completed_work_orders=data["completed_work_orders"],
            total_alerts=data["total_alerts"],
        )

    def get_revenue_trend(
        self,
        tenant_id: UUID,
        interval: str = "monthly",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> RevenueTrendResponse:
        normalized_interval = interval.lower()
        if normalized_interval not in ("monthly", "weekly"):
            normalized_interval = "monthly"

        trends_data = self._repo.get_revenue_trend(
            tenant_id=tenant_id,
            interval=normalized_interval,
            start_date=start_date,
            end_date=end_date,
        )

        trend_items = [RevenueTrendItem(**item) for item in trends_data]
        return RevenueTrendResponse(
            tenant_id=tenant_id,
            interval=normalized_interval,
            trends=trend_items,
        )

    def get_work_order_performance(self, tenant_id: UUID) -> WorkOrderPerformanceResponse:
        data = self._repo.get_work_order_performance(tenant_id)
        return WorkOrderPerformanceResponse(
            tenant_id=UUID(data["tenant_id"]),
            average_cycle_time_hours=data["average_cycle_time_hours"],
            average_lead_time_hours=data["average_lead_time_hours"],
            on_time_percentage=data["on_time_percentage"],
            technicians=[TechnicianPerformance(**t) for t in data["technicians"]],
        )

    def get_fleet_health(self, tenant_id: UUID) -> FleetHealthResponse:
        data = self._repo.get_fleet_health_overview(tenant_id)
        return FleetHealthResponse(
            tenant_id=UUID(data["tenant_id"]),
            total_vehicles_monitored=data["total_vehicles_monitored"],
            critical_alerts=data["critical_alerts"],
            warning_alerts=data["warning_alerts"],
            fleet_health_score=data["fleet_health_score"],
            top_dtc_codes=[DtcCodeSummary(**dtc) for dtc in data["top_dtc_codes"]],
        )
