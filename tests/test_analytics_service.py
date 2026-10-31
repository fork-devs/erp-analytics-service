from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4
import pytest

from app.services.analytics_service import AnalyticsService


@pytest.fixture
def mock_repo():
    return MagicMock()


def test_service_get_summary(mock_repo):
    service = AnalyticsService(repository=mock_repo)
    tenant_id = uuid4()
    mock_repo.get_workshop_summary.return_value = {
        "tenant_id": str(tenant_id),
        "total_revenue": 24500.0,
        "active_work_orders": 8,
        "completed_work_orders": 45,
        "total_alerts": 2,
    }

    summary = service.get_summary(tenant_id)

    assert summary.tenant_id == tenant_id
    assert summary.total_revenue == 24500.0
    assert summary.active_work_orders == 8
    assert summary.completed_work_orders == 45
    assert summary.total_alerts == 2


def test_service_get_revenue_trend(mock_repo):
    service = AnalyticsService(repository=mock_repo)
    tenant_id = uuid4()
    mock_repo.get_revenue_trend.return_value = [
        {
            "period": "202610",
            "gross_revenue": 10000.0,
            "parts_cost": 3000.0,
            "labor_cost": 2000.0,
            "gross_margin_percentage": 50.0,
        }
    ]

    res = service.get_revenue_trend(tenant_id, interval="monthly")

    assert res.tenant_id == tenant_id
    assert res.interval == "monthly"
    assert len(res.trends) == 1
    assert res.trends[0].period == "202610"
    assert res.trends[0].gross_margin_percentage == 50.0


def test_service_get_work_order_performance(mock_repo):
    service = AnalyticsService(repository=mock_repo)
    tenant_id = uuid4()
    mock_repo.get_work_order_performance.return_value = {
        "tenant_id": str(tenant_id),
        "average_cycle_time_hours": 3.8,
        "average_lead_time_hours": 7.5,
        "on_time_percentage": 92.0,
        "technicians": [
            {
                "technician_id": "tech-01",
                "jobs_completed": 12,
                "avg_cycle_time_hours": 3.5,
            }
        ],
    }

    res = service.get_work_order_performance(tenant_id)

    assert res.tenant_id == tenant_id
    assert res.average_cycle_time_hours == 3.8
    assert res.on_time_percentage == 92.0
    assert len(res.technicians) == 1
    assert res.technicians[0].technician_id == "tech-01"


def test_service_get_fleet_health(mock_repo):
    service = AnalyticsService(repository=mock_repo)
    tenant_id = uuid4()
    mock_repo.get_fleet_health_overview.return_value = {
        "tenant_id": str(tenant_id),
        "total_vehicles_monitored": 15,
        "critical_alerts": 1,
        "warning_alerts": 3,
        "fleet_health_score": 96.0,
        "top_dtc_codes": [{"dtc_code": "P0300", "occurrences": 2}],
    }

    res = service.get_fleet_health(tenant_id)

    assert res.tenant_id == tenant_id
    assert res.total_vehicles_monitored == 15
    assert res.fleet_health_score == 96.0
    assert len(res.top_dtc_codes) == 1
    assert res.top_dtc_codes[0].dtc_code == "P0300"
