from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import logging

from clickhouse_connect.driver.client import Client
from app.core.clickhouse import ClickHouseManager, clickhouse_manager

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Repository handling all ClickHouse queries with strict multi-tenant isolation."""

    def __init__(self, manager: Optional[ClickHouseManager] = None):
        self._manager = manager or clickhouse_manager

    @property
    def client(self) -> Client:
        return self._manager.get_client()

    def _validate_tenant(self, tenant_id: UUID) -> str:
        if not tenant_id:
            raise ValueError("tenant_id is strictly required for multi-tenant isolation")
        return str(tenant_id)

    # -------------------------------------------------------------
    # Ingestion Methods (Batched Insertions)
    # -------------------------------------------------------------
    def insert_invoices(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        columns = [
            "event_id", "tenant_id", "invoice_id", "work_order_id",
            "customer_id", "total_amount", "subtotal", "tax_amount",
            "parts_cost", "labor_cost", "status", "issued_at", "event_date"
        ]
        data = [
            [
                str(r["event_id"]), str(r["tenant_id"]), str(r["invoice_id"]),
                str(r["work_order_id"]) if r.get("work_order_id") else None,
                str(r["customer_id"]), float(r["total_amount"]),
                float(r.get("subtotal", 0.0)), float(r.get("tax_amount", 0.0)),
                float(r.get("parts_cost", 0.0)), float(r.get("labor_cost", 0.0)),
                str(r.get("status", "ISSUED")), r["issued_at"],
                r.get("event_date") or r["issued_at"].date()
            ]
            for r in records
        ]
        self.client.insert("analytics_invoices", data, column_names=columns)

    def insert_payments(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        columns = [
            "event_id", "tenant_id", "payment_id", "invoice_id",
            "amount", "payment_method", "status", "paid_at", "event_date"
        ]
        data = [
            [
                str(r["event_id"]), str(r["tenant_id"]), str(r["payment_id"]),
                str(r["invoice_id"]), float(r["amount"]),
                str(r.get("payment_method", "CREDIT_CARD")),
                str(r.get("status", "COMPLETED")), r["paid_at"],
                r.get("event_date") or r["paid_at"].date()
            ]
            for r in records
        ]
        self.client.insert("analytics_payments", data, column_names=columns)

    def insert_work_orders(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        columns = [
            "event_id", "tenant_id", "work_order_id", "vehicle_id",
            "technician_id", "status", "cycle_time_hours", "lead_time_hours",
            "is_completed", "completed_on_time", "labor_cost", "parts_cost",
            "completed_at", "event_date"
        ]
        data = [
            [
                str(r["event_id"]), str(r["tenant_id"]), str(r["work_order_id"]),
                str(r["vehicle_id"]),
                str(r["technician_id"]) if r.get("technician_id") else None,
                str(r.get("status", "COMPLETED")), float(r.get("cycle_time_hours", 0.0)),
                float(r.get("lead_time_hours", 0.0)), int(r.get("is_completed", 1)),
                int(r.get("completed_on_time", 1)), float(r.get("labor_cost", 0.0)),
                float(r.get("parts_cost", 0.0)), r.get("completed_at"),
                r.get("event_date") or (r["completed_at"].date() if r.get("completed_at") else date.today())
            ]
            for r in records
        ]
        self.client.insert("analytics_work_orders", data, column_names=columns)

    def insert_stock_movements(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        columns = [
            "event_id", "tenant_id", "movement_id", "part_id",
            "quantity", "unit_cost", "total_cost", "movement_type",
            "moved_at", "event_date"
        ]
        data = [
            [
                str(r["event_id"]), str(r["tenant_id"]), str(r["movement_id"]),
                str(r["part_id"]), int(r["quantity"]),
                float(r.get("unit_cost", 0.0)), float(r.get("total_cost", 0.0)),
                str(r.get("movement_type", "OUT")), r["moved_at"],
                r.get("event_date") or r["moved_at"].date()
            ]
            for r in records
        ]
        self.client.insert("analytics_stock_movements", data, column_names=columns)

    def insert_telemetry_alerts(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        columns = [
            "event_id", "tenant_id", "vehicle_id", "device_id",
            "alert_type", "severity", "dtc_code", "description",
            "alert_timestamp", "event_date"
        ]
        data = [
            [
                str(r["event_id"]), str(r["tenant_id"]), str(r["vehicle_id"]),
                str(r.get("device_id", "")), str(r.get("alert_type", "ANOMALY")),
                str(r.get("severity", "WARNING")), str(r.get("dtc_code", "")),
                str(r.get("description", "")), r["alert_timestamp"],
                r.get("event_date") or r["alert_timestamp"].date()
            ]
            for r in records
        ]
        self.client.insert("analytics_telemetry_alerts", data, column_names=columns)

    def insert_branch_snapshots(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        columns = [
            "snapshot_id", "tenant_id", "branch_id", "snapshot_date",
            "total_revenue", "completed_work_orders_count", "total_appointments_count",
            "low_stock_alerts_count", "dtc_alerts_count", "event_date", "updated_at"
        ]
        data = [
            [
                str(r.get("snapshot_id", uuid4())),
                str(r["tenant_id"]),
                str(r["branch_id"]),
                r["snapshot_date"],
                max(0.0, float(r.get("total_revenue", 0.0))),
                max(0, int(r.get("completed_work_orders_count", 0))),
                max(0, int(r.get("total_appointments_count", 0))),
                max(0, int(r.get("low_stock_alerts_count", 0))),
                max(0, int(r.get("dtc_alerts_count", 0))),
                r.get("event_date") or r["snapshot_date"],
                r.get("updated_at") or datetime.now(timezone.utc),
            ]
            for r in records
        ]
        self.client.insert("analytics_branch_daily_snapshots", data, column_names=columns)

    # -------------------------------------------------------------
    # Query Methods (Multi-Tenant Isolated)
    # -------------------------------------------------------------
    def get_workshop_summary(self, tenant_id: UUID) -> Dict[str, Any]:
        tid = self._validate_tenant(tenant_id)

        # Total revenue
        rev_query = """
            SELECT coalesce(sum(total_amount), 0.0)
            FROM analytics_invoices FINAL
            WHERE tenant_id = %(tenant_id)s
        """
        total_revenue = float(self.client.command(rev_query, parameters={"tenant_id": tid}) or 0.0)

        # Active & completed work orders
        wo_query = """
            SELECT
                countIf(is_completed = 0) AS active_orders,
                countIf(is_completed = 1) AS completed_orders
            FROM analytics_work_orders FINAL
            WHERE tenant_id = %(tenant_id)s
        """
        wo_result = self.client.query(wo_query, parameters={"tenant_id": tid})
        active_wo, completed_wo = 0, 0
        if wo_result.result_rows:
            active_wo, completed_wo = wo_result.result_rows[0]

        # Open alerts
        alert_query = """
            SELECT count()
            FROM analytics_telemetry_alerts FINAL
            WHERE tenant_id = %(tenant_id)s
        """
        open_alerts = int(self.client.command(alert_query, parameters={"tenant_id": tid}) or 0)

        return {
            "tenant_id": tid,
            "total_revenue": total_revenue,
            "active_work_orders": int(active_wo),
            "completed_work_orders": int(completed_wo),
            "total_alerts": open_alerts,
        }

    def get_revenue_trend(
        self,
        tenant_id: UUID,
        interval: str = "monthly",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        tid = self._validate_tenant(tenant_id)

        period_expr = "toYYYYMM(event_date)" if interval == "monthly" else "toMonday(event_date)"
        period_format = "formatDateTime(toDate(toMonday(event_date)), '%%Y-%%m-%%d')" if interval != "monthly" else "toString(toYYYYMM(event_date))"

        where_clause = "WHERE tenant_id = %(tenant_id)s"
        params: Dict[str, Any] = {"tenant_id": tid}

        if start_date:
            where_clause += " AND event_date >= %(start_date)s"
            params["start_date"] = str(start_date)
        if end_date:
            where_clause += " AND event_date <= %(end_date)s"
            params["end_date"] = str(end_date)

        query = f"""
            SELECT
                {period_format} AS period,
                sum(total_amount) AS gross_revenue,
                sum(parts_cost) AS total_parts_cost,
                sum(labor_cost) AS total_labor_cost,
                if(sum(total_amount) > 0,
                   round((sum(total_amount) - sum(parts_cost) - sum(labor_cost)) * 100.0 / sum(total_amount), 2),
                   0.0) AS gross_margin_percentage
            FROM analytics_invoices FINAL
            {where_clause}
            GROUP BY {period_expr}, period
            ORDER BY {period_expr} ASC
        """

        result = self.client.query(query, parameters=params)
        trends = []
        for row in result.result_rows:
            trends.append({
                "period": str(row[0]),
                "gross_revenue": float(row[1]),
                "parts_cost": float(row[2]),
                "labor_cost": float(row[3]),
                "gross_margin_percentage": float(row[4]),
            })
        return trends

    def get_work_order_performance(self, tenant_id: UUID) -> Dict[str, Any]:
        tid = self._validate_tenant(tenant_id)

        summary_query = """
            SELECT
                coalesce(round(avg(cycle_time_hours), 2), 0.0) AS avg_cycle_time,
                coalesce(round(avg(lead_time_hours), 2), 0.0) AS avg_lead_time,
                if(count() > 0, round(countIf(completed_on_time = 1) * 100.0 / count(), 2), 100.0) AS on_time_percentage
            FROM analytics_work_orders FINAL
            WHERE tenant_id = %(tenant_id)s AND is_completed = 1
        """
        summary_res = self.client.query(summary_query, parameters={"tenant_id": tid})
        avg_cycle, avg_lead, on_time_pct = 0.0, 0.0, 100.0
        if summary_res.result_rows:
            avg_cycle, avg_lead, on_time_pct = summary_res.result_rows[0]

        tech_query = """
            SELECT
                toString(technician_id) AS technician_id,
                count() AS jobs_completed,
                round(avg(cycle_time_hours), 2) AS avg_cycle_time
            FROM analytics_work_orders FINAL
            WHERE tenant_id = %(tenant_id)s AND is_completed = 1 AND isNotNull(technician_id)
            GROUP BY technician_id
            ORDER BY jobs_completed DESC
            LIMIT 20
        """
        tech_res = self.client.query(tech_query, parameters={"tenant_id": tid})
        technicians = [
            {
                "technician_id": str(r[0]),
                "jobs_completed": int(r[1]),
                "avg_cycle_time_hours": float(r[2]),
            }
            for r in tech_res.result_rows
        ]

        return {
            "tenant_id": tid,
            "average_cycle_time_hours": float(avg_cycle),
            "average_lead_time_hours": float(avg_lead),
            "on_time_percentage": float(on_time_pct),
            "technicians": technicians,
        }

    def get_fleet_health_overview(self, tenant_id: UUID) -> Dict[str, Any]:
        tid = self._validate_tenant(tenant_id)

        # Vehicle counts & alert stats
        stats_query = """
            SELECT
                uniqExact(vehicle_id) AS total_vehicles_monitored,
                countIf(severity = 'CRITICAL') AS critical_alerts,
                countIf(severity = 'WARNING') AS warning_alerts
            FROM analytics_telemetry_alerts FINAL
            WHERE tenant_id = %(tenant_id)s
        """
        stats_res = self.client.query(stats_query, parameters={"tenant_id": tid})
        total_vehicles, crit_alerts, warn_alerts = 0, 0, 0
        if stats_res.result_rows:
            total_vehicles, crit_alerts, warn_alerts = stats_res.result_rows[0]

        # Top Diagnostic Trouble Codes (DTCs)
        dtc_query = """
            SELECT
                dtc_code,
                count() AS occurrences
            FROM analytics_telemetry_alerts FINAL
            WHERE tenant_id = %(tenant_id)s AND dtc_code != ''
            GROUP BY dtc_code
            ORDER BY occurrences DESC
            LIMIT 5
        """
        dtc_res = self.client.query(dtc_query, parameters={"tenant_id": tid})
        top_dtcs = [
            {"dtc_code": str(r[0]), "occurrences": int(r[1])}
            for r in dtc_res.result_rows
        ]

        # Calculate fleet health score (100 - penalties for alerts)
        base_score = 100.0
        if total_vehicles > 0:
            penalty = (float(crit_alerts) * 15.0 + float(warn_alerts) * 5.0) / float(total_vehicles)
            fleet_health_score = max(0.0, round(base_score - penalty, 1))
        else:
            fleet_health_score = 100.0

        return {
            "tenant_id": tid,
            "total_vehicles_monitored": int(total_vehicles),
            "critical_alerts": int(crit_alerts),
            "warning_alerts": int(warn_alerts),
            "fleet_health_score": float(fleet_health_score),
            "top_dtc_codes": top_dtcs,
        }

    # -------------------------------------------------------------
    # Branch Daily Snapshots & Network Consolidated Queries
    # -------------------------------------------------------------
    def get_branch_daily_snapshot(
        self, tenant_id: UUID, branch_id: UUID, snapshot_date: date
    ) -> Optional[Dict[str, Any]]:
        tid = self._validate_tenant(tenant_id)
        bid = str(branch_id)
        query = """
            SELECT
                snapshot_id,
                tenant_id,
                branch_id,
                snapshot_date,
                total_revenue,
                completed_work_orders_count,
                total_appointments_count,
                low_stock_alerts_count,
                dtc_alerts_count
            FROM analytics_branch_daily_snapshots FINAL
            WHERE tenant_id = %(tenant_id)s
              AND branch_id = %(branch_id)s
              AND snapshot_date = %(snapshot_date)s
            LIMIT 1
        """
        result = self.client.query(
            query,
            parameters={
                "tenant_id": tid,
                "branch_id": bid,
                "snapshot_date": str(snapshot_date),
            },
        )
        if not result.result_rows:
            return None
        row = result.result_rows[0]
        return {
            "snapshot_id": UUID(str(row[0])),
            "tenant_id": UUID(str(row[1])),
            "branch_id": UUID(str(row[2])),
            "snapshot_date": row[3],
            "total_revenue": max(0.0, float(row[4])),
            "completed_work_orders_count": max(0, int(row[5])),
            "total_appointments_count": max(0, int(row[6])),
            "low_stock_alerts_count": max(0, int(row[7])),
            "dtc_alerts_count": max(0, int(row[8])),
        }

    def get_branch_daily_summary(
        self, tenant_id: UUID, branch_id: UUID, business_date: date
    ) -> Dict[str, Any]:
        snapshot = self.get_branch_daily_snapshot(tenant_id, branch_id, business_date)
        if snapshot:
            return {
                "branch_id": snapshot["branch_id"],
                "total_revenue": snapshot["total_revenue"],
                "completed_work_orders_count": snapshot["completed_work_orders_count"],
                "total_appointments_count": snapshot["total_appointments_count"],
                "low_stock_alerts_count": snapshot["low_stock_alerts_count"],
                "dtc_alerts_count": snapshot["dtc_alerts_count"],
            }
        return {
            "branch_id": branch_id,
            "total_revenue": 0.0,
            "completed_work_orders_count": 0,
            "total_appointments_count": 0,
            "low_stock_alerts_count": 0,
            "dtc_alerts_count": 0,
        }

    def get_branch_financial_range(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        tid = self._validate_tenant(tenant_id)
        bid = str(branch_id)
        query = """
            SELECT
                snapshot_id,
                branch_id,
                snapshot_date,
                total_revenue,
                completed_work_orders_count,
                total_appointments_count,
                low_stock_alerts_count,
                dtc_alerts_count
            FROM analytics_branch_daily_snapshots FINAL
            WHERE tenant_id = %(tenant_id)s
              AND branch_id = %(branch_id)s
              AND snapshot_date >= %(start_date)s
              AND snapshot_date <= %(end_date)s
            ORDER BY snapshot_date ASC
        """
        result = self.client.query(
            query,
            parameters={
                "tenant_id": tid,
                "branch_id": bid,
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )
        snapshots = []
        for row in result.result_rows:
            snapshots.append({
                "id": UUID(str(row[0])),
                "branch_id": UUID(str(row[1])),
                "snapshot_date": row[2],
                "total_revenue": max(0.0, float(row[3])),
                "completed_work_orders_count": max(0, int(row[4])),
                "total_appointments_count": max(0, int(row[5])),
                "low_stock_alerts_count": max(0, int(row[6])),
                "dtc_alerts_count": max(0, int(row[7])),
            })
        return snapshots

    def get_network_summary(
        self, tenant_id: UUID, business_date: date
    ) -> Dict[str, Any]:
        tid = self._validate_tenant(tenant_id)
        query = """
            SELECT
                uniqExact(branch_id) AS total_active_branches,
                coalesce(sum(total_revenue), 0.0) AS total_network_revenue,
                coalesce(sum(completed_work_orders_count), 0) AS total_network_completed_work_orders,
                coalesce(sum(total_appointments_count), 0) AS total_network_appointments,
                coalesce(sum(dtc_alerts_count), 0) AS total_network_dtc_alerts
            FROM analytics_branch_daily_snapshots FINAL
            WHERE tenant_id = %(tenant_id)s
              AND snapshot_date = %(business_date)s
        """
        result = self.client.query(
            query,
            parameters={
                "tenant_id": tid,
                "business_date": str(business_date),
            },
        )
        if not result.result_rows:
            return {
                "total_active_branches_count": 0,
                "total_network_revenue": 0.0,
                "total_network_completed_work_orders": 0,
                "total_network_appointments": 0,
                "total_network_dtc_alerts": 0,
            }
        row = result.result_rows[0]
        return {
            "total_active_branches_count": int(row[0]),
            "total_network_revenue": max(0.0, float(row[1])),
            "total_network_completed_work_orders": max(0, int(row[2])),
            "total_network_appointments": max(0, int(row[3])),
            "total_network_dtc_alerts": max(0, int(row[4])),
        }

    def apply_delta_to_snapshot(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        snapshot_date: date,
        revenue_delta: float = 0.0,
        completed_wo_delta: int = 0,
        appointments_delta: int = 0,
        dtc_alerts_delta: int = 0,
        low_stock_alerts_count: Optional[int] = None,
    ) -> None:
        """Applies deltas to the daily snapshot for the given branch and date, with clamping >= 0."""
        existing = self.get_branch_daily_snapshot(tenant_id, branch_id, snapshot_date)
        if existing:
            new_rev = max(0.0, existing["total_revenue"] + revenue_delta)
            new_wo = max(0, existing["completed_work_orders_count"] + completed_wo_delta)
            new_app = max(0, existing["total_appointments_count"] + appointments_delta)
            new_dtc = max(0, existing["dtc_alerts_count"] + dtc_alerts_delta)
            new_stock = (
                low_stock_alerts_count
                if low_stock_alerts_count is not None
                else existing["low_stock_alerts_count"]
            )
            snapshot_id = existing["snapshot_id"]
        else:
            new_rev = max(0.0, revenue_delta)
            new_wo = max(0, completed_wo_delta)
            new_app = max(0, appointments_delta)
            new_dtc = max(0, dtc_alerts_delta)
            new_stock = max(0, low_stock_alerts_count or 0)
            snapshot_id = uuid4()

        self.insert_branch_snapshots([{
            "snapshot_id": snapshot_id,
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "snapshot_date": snapshot_date,
            "total_revenue": new_rev,
            "completed_work_orders_count": new_wo,
            "total_appointments_count": new_app,
            "low_stock_alerts_count": new_stock,
            "dtc_alerts_count": new_dtc,
            "updated_at": datetime.now(timezone.utc),
        }])

