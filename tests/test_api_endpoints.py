from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.repositories.analytics_repository import AnalyticsRepository


@pytest.fixture
def test_client():
    mock_repo = MagicMock(spec=AnalyticsRepository)
    mock_ch_manager = MagicMock()
    mock_kafka_worker = MagicMock()
    mock_kafka_worker.start = AsyncMock()
    mock_kafka_worker.stop = AsyncMock()

    app.state.analytics_repo = mock_repo
    app.state.clickhouse_manager = mock_ch_manager
    app.state.kafka_worker = mock_kafka_worker

    with TestClient(app) as client:
        yield client, mock_repo, mock_ch_manager


def test_healthz_endpoint(test_client):
    client, _, _ = test_client
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readyz_connected(test_client):
    client, _, mock_ch = test_client
    mock_client = MagicMock()
    mock_client.command.return_value = "1"
    mock_ch.get_client.return_value = mock_client

    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "clickhouse": "connected"}


def test_readyz_disconnected(test_client):
    client, _, mock_ch = test_client
    mock_client = MagicMock()
    mock_client.command.side_effect = Exception("Connection refused")
    mock_ch.get_client.return_value = mock_client

    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_get_summary_endpoint(test_client):
    client, mock_repo, _ = test_client
    tenant_id = uuid4()
    mock_repo.get_workshop_summary.return_value = {
        "tenant_id": str(tenant_id),
        "total_revenue": 18250.0,
        "active_work_orders": 4,
        "completed_work_orders": 32,
        "total_alerts": 1,
    }

    response = client.get(
        "/api/v1/analytics/summary",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["total_revenue"] == 18250.0
    assert data["active_work_orders"] == 4
    assert data["completed_work_orders"] == 32
    assert data["total_alerts"] == 1


def test_get_revenue_trend_endpoint(test_client):
    client, mock_repo, _ = test_client
    tenant_id = uuid4()
    mock_repo.get_revenue_trend.return_value = [
        {
            "period": "202610",
            "gross_revenue": 50000.0,
            "parts_cost": 15000.0,
            "labor_cost": 10000.0,
            "gross_margin_percentage": 50.0,
        }
    ]

    response = client.get(
        "/api/v1/analytics/revenue/trend?interval=monthly&start_date=2026-10-01&end_date=2026-10-31",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == str(tenant_id)
    assert data["interval"] == "monthly"
    assert len(data["trends"]) == 1
    assert data["trends"][0]["gross_revenue"] == 50000.0


def test_get_work_orders_performance_endpoint(test_client):
    client, mock_repo, _ = test_client
    tenant_id = uuid4()
    mock_repo.get_work_order_performance.return_value = {
        "tenant_id": str(tenant_id),
        "average_cycle_time_hours": 4.2,
        "average_lead_time_hours": 8.0,
        "on_time_percentage": 95.0,
        "technicians": [
            {
                "technician_id": "tech-uuid-1",
                "jobs_completed": 20,
                "avg_cycle_time_hours": 4.0,
            }
        ],
    }

    response = client.get(
        "/api/v1/analytics/work-orders/performance",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["average_cycle_time_hours"] == 4.2
    assert data["on_time_percentage"] == 95.0
    assert len(data["technicians"]) == 1
    assert data["technicians"][0]["technician_id"] == "tech-uuid-1"


def test_get_fleet_health_endpoint(test_client):
    client, mock_repo, _ = test_client
    tenant_id = uuid4()
    mock_repo.get_fleet_health_overview.return_value = {
        "tenant_id": str(tenant_id),
        "total_vehicles_monitored": 25,
        "critical_alerts": 2,
        "warning_alerts": 5,
        "fleet_health_score": 93.0,
        "top_dtc_codes": [{"dtc_code": "P0300", "occurrences": 3}],
    }

    response = client.get(
        "/api/v1/analytics/fleet/health-overview",
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_vehicles_monitored"] == 25
    assert data["fleet_health_score"] == 93.0
    assert len(data["top_dtc_codes"]) == 1


def test_invalid_tenant_id_header(test_client):
    client, _, _ = test_client
    response = client.get(
        "/api/v1/analytics/summary",
        headers={"X-Tenant-ID": "not-a-valid-uuid"},
    )
    assert response.status_code == 400
    assert "Invalid X-Tenant-ID header" in response.json()["detail"]
