from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID
import zoneinfo
from pydantic import BaseModel, ConfigDict, Field

from app.repositories.analytics_repository import AnalyticsRepository

LIMA_TZ = zoneinfo.ZoneInfo("America/Lima")


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


class BranchDailySummaryResponse(BaseModel):
    branch_id: UUID = Field(..., serialization_alias="branchId")
    total_revenue: float = Field(default=0.0, ge=0.0, serialization_alias="totalRevenue")
    completed_work_orders_count: int = Field(default=0, ge=0, serialization_alias="completedWorkOrdersCount")
    total_appointments_count: int = Field(default=0, ge=0, serialization_alias="totalAppointmentsCount")
    low_stock_alerts_count: int = Field(default=0, ge=0, serialization_alias="lowStockAlertsCount")
    dtc_alerts_count: int = Field(default=0, ge=0, serialization_alias="dtcAlertsCount")

    model_config = ConfigDict(populate_by_name=True)


class BranchFinancialSnapshotItem(BaseModel):
    id: UUID
    branch_id: UUID = Field(..., serialization_alias="branchId")
    snapshot_date: date = Field(..., serialization_alias="snapshotDate")
    total_revenue: float = Field(default=0.0, ge=0.0, serialization_alias="totalRevenue")
    completed_work_orders_count: int = Field(default=0, ge=0, serialization_alias="completedWorkOrdersCount")
    total_appointments_count: int = Field(default=0, ge=0, serialization_alias="totalAppointmentsCount")
    low_stock_alerts_count: int = Field(default=0, ge=0, serialization_alias="lowStockAlertsCount")
    dtc_alerts_count: int = Field(default=0, ge=0, serialization_alias="dtcAlertsCount")

    model_config = ConfigDict(populate_by_name=True)


class NetworkSummaryResponse(BaseModel):
    total_active_branches_count: int = Field(default=0, ge=0, serialization_alias="totalActiveBranchesCount")
    total_network_revenue: float = Field(default=0.0, ge=0.0, serialization_alias="totalNetworkRevenue")
    total_network_completed_work_orders: int = Field(default=0, ge=0, serialization_alias="totalNetworkCompletedWorkOrders")
    total_network_appointments: int = Field(default=0, ge=0, serialization_alias="totalNetworkAppointments")
    total_network_dtc_alerts: int = Field(default=0, ge=0, serialization_alias="totalNetworkDtcAlerts")

    model_config = ConfigDict(populate_by_name=True)


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

    def get_branch_summary(self, tenant_id: UUID, branch_id: UUID) -> BranchDailySummaryResponse:
        business_date = datetime.now(LIMA_TZ).date()
        data = self._repo.get_branch_daily_summary(tenant_id, branch_id, business_date)
        return BranchDailySummaryResponse(
            branch_id=data["branch_id"],
            total_revenue=data["total_revenue"],
            completed_work_orders_count=data["completed_work_orders_count"],
            total_appointments_count=data["total_appointments_count"],
            low_stock_alerts_count=data["low_stock_alerts_count"],
            dtc_alerts_count=data["dtc_alerts_count"],
        )

    def get_branch_financial(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[BranchFinancialSnapshotItem]:
        today = datetime.now(LIMA_TZ).date()
        effective_end = end_date or today
        effective_start = start_date or (effective_end - timedelta(days=30))

        if effective_start > effective_end:
            raise ValueError(f"startDate ({effective_start}) cannot be after endDate ({effective_end})")

        if (effective_end - effective_start).days > 365:
            raise ValueError("Date range cannot exceed 365 days")

        snapshots = self._repo.get_branch_financial_range(
            tenant_id=tenant_id,
            branch_id=branch_id,
            start_date=effective_start,
            end_date=effective_end,
        )
        return [BranchFinancialSnapshotItem(**s) for s in snapshots]

    def get_network_summary(self, tenant_id: UUID) -> NetworkSummaryResponse:
        business_date = datetime.now(LIMA_TZ).date()
        data = self._repo.get_network_summary(tenant_id, business_date)
        return NetworkSummaryResponse(
            total_active_branches_count=data["total_active_branches_count"],
            total_network_revenue=data["total_network_revenue"],
            total_network_completed_work_orders=data["total_network_completed_work_orders"],
            total_network_appointments=data["total_network_appointments"],
            total_network_dtc_alerts=data["total_network_dtc_alerts"],
        )

