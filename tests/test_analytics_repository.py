from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import uuid4
import pytest

from app.repositories.analytics_repository import AnalyticsRepository


@pytest.fixture
def mock_clickhouse_manager():
    manager = MagicMock()
    mock_client = MagicMock()
    manager.get_client.return_value = mock_client
    return manager, mock_client


def test_tenant_id_validation(mock_clickhouse_manager):
    manager, _ = mock_clickhouse_manager
    repo = AnalyticsRepository(manager=manager)
    with pytest.raises(ValueError, match="strictly required"):
        repo.get_workshop_summary(None)  # type: ignore


def test_insert_invoices(mock_clickhouse_manager):
    manager, client = mock_clickhouse_manager
    repo = AnalyticsRepository(manager=manager)

    tenant_id = uuid4()
    records = [
        {
            "event_id": uuid4(),
            "tenant_id": tenant_id,
            "invoice_id": uuid4(),
            "customer_id": uuid4(),
            "total_amount": 500.0,
            "subtotal": 420.0,
            "tax_amount": 80.0,
            "parts_cost": 200.0,
            "labor_cost": 100.0,
            "issued_at": datetime.now(),
        }
    ]

    repo.insert_invoices(records)
    client.insert.assert_called_once()
    table_name, data = client.insert.call_args[0][:2]
    assert table_name == "analytics_invoices"
    assert len(data) == 1
    assert data[0][1] == str(tenant_id)


def test_get_workshop_summary(mock_clickhouse_manager):
    manager, client = mock_clickhouse_manager
    repo = AnalyticsRepository(manager=manager)

    tenant_id = uuid4()
    # Mock return values
    client.command.side_effect = ["15000.50", "3"]  # total_revenue, open_alerts
    query_result = MagicMock()
    query_result.result_rows = [[5, 20]]  # active_orders, completed_orders
    client.query.return_value = query_result

    summary = repo.get_workshop_summary(tenant_id)

    assert summary["tenant_id"] == str(tenant_id)
    assert summary["total_revenue"] == 15000.50
    assert summary["active_work_orders"] == 5
    assert summary["completed_work_orders"] == 20
    assert summary["total_alerts"] == 3


def test_get_revenue_trend(mock_clickhouse_manager):
    manager, client = mock_clickhouse_manager
    repo = AnalyticsRepository(manager=manager)

    tenant_id = uuid4()
    query_result = MagicMock()
    query_result.result_rows = [
        ["202610", 10000.0, 3000.0, 2000.0, 50.0],
        ["202611", 12000.0, 4000.0, 2500.0, 45.83],
    ]
    client.query.return_value = query_result

    trends = repo.get_revenue_trend(tenant_id, interval="monthly", start_date=date(2026, 10, 1), end_date=date(2026, 11, 30))

    assert len(trends) == 2
    assert trends[0]["period"] == "202610"
    assert trends[0]["gross_revenue"] == 10000.0
    assert trends[0]["gross_margin_percentage"] == 50.0


def test_get_work_order_performance(mock_clickhouse_manager):
    manager, client = mock_clickhouse_manager
    repo = AnalyticsRepository(manager=manager)

    tenant_id = uuid4()
    summary_result = MagicMock()
    summary_result.result_rows = [[4.5, 8.2, 94.5]]
    tech_result = MagicMock()
    tech_id = str(uuid4())
    tech_result.result_rows = [[tech_id, 15, 3.8]]

    client.query.side_effect = [summary_result, tech_result]

    perf = repo.get_work_order_performance(tenant_id)

    assert perf["average_cycle_time_hours"] == 4.5
    assert perf["average_lead_time_hours"] == 8.2
    assert perf["on_time_percentage"] == 94.5
    assert len(perf["technicians"]) == 1
    assert perf["technicians"][0]["technician_id"] == tech_id
    assert perf["technicians"][0]["jobs_completed"] == 15


def test_get_fleet_health_overview(mock_clickhouse_manager):
    manager, client = mock_clickhouse_manager
    repo = AnalyticsRepository(manager=manager)

    tenant_id = uuid4()
    stats_result = MagicMock()
    stats_result.result_rows = [[10, 2, 4]]  # 10 vehicles, 2 critical, 4 warning
    dtc_result = MagicMock()
    dtc_result.result_rows = [["P0300", 5], ["P0171", 3]]

    client.query.side_effect = [stats_result, dtc_result]

    fleet = repo.get_fleet_health_overview(tenant_id)

    assert fleet["total_vehicles_monitored"] == 10
    assert fleet["critical_alerts"] == 2
    assert fleet["warning_alerts"] == 4
    # penalty = (2 * 15 + 4 * 5) / 10 = (30 + 20) / 10 = 5.0 -> score = 95.0
    assert fleet["fleet_health_score"] == 95.0
    assert len(fleet["top_dtc_codes"]) == 2


def test_branch_daily_snapshot_methods(mock_clickhouse_manager):
    manager, client = mock_clickhouse_manager
    repo = AnalyticsRepository(manager=manager)

    tenant_id = uuid4()
    branch_id = uuid4()
    today = date(2026, 10, 31)

    # 1. Test insert_branch_snapshots
    repo.insert_branch_snapshots(
        [
            {
                "snapshot_id": uuid4(),
                "tenant_id": tenant_id,
                "branch_id": branch_id,
                "snapshot_date": today,
                "total_revenue": 1250.0,
                "completed_work_orders_count": 4,
                "total_appointments_count": 7,
                "low_stock_alerts_count": 2,
                "dtc_alerts_count": 1,
            }
        ]
    )
    client.insert.assert_called_once()
    assert client.insert.call_args[0][0] == "analytics_branch_daily_snapshots"

    # 2. Test get_branch_daily_summary with existing data
    query_result = MagicMock()
    query_result.result_rows = [
        [
            str(uuid4()),
            str(tenant_id),
            str(branch_id),
            today,
            1250.0,
            4,
            7,
            2,
            1,
        ]
    ]
    client.query.return_value = query_result

    summary = repo.get_branch_daily_summary(tenant_id, branch_id, today)
    assert summary["branch_id"] == branch_id
    assert summary["total_revenue"] == 1250.0
    assert summary["completed_work_orders_count"] == 4
    assert summary["total_appointments_count"] == 7
    assert summary["low_stock_alerts_count"] == 2
    assert summary["dtc_alerts_count"] == 1

    # 3. Test get_branch_financial_range
    query_result_range = MagicMock()
    query_result_range.result_rows = [
        [str(uuid4()), str(branch_id), date(2026, 10, 30), 950.0, 3, 5, 2, 0],
        [str(uuid4()), str(branch_id), date(2026, 10, 31), 1250.0, 4, 7, 2, 1],
    ]
    client.query.return_value = query_result_range
    fin_history = repo.get_branch_financial_range(tenant_id, branch_id, date(2026, 10, 1), today)
    assert len(fin_history) == 2
    assert fin_history[0]["total_revenue"] == 950.0
    assert fin_history[1]["total_revenue"] == 1250.0

    # 4. Test get_network_summary
    network_result = MagicMock()
    network_result.result_rows = [[3, 4850.0, 14, 22, 3]]
    client.query.return_value = network_result
    net_summary = repo.get_network_summary(tenant_id, today)
    assert net_summary["total_active_branches_count"] == 3
    assert net_summary["total_network_revenue"] == 4850.0
    assert net_summary["total_network_completed_work_orders"] == 14
    assert net_summary["total_network_appointments"] == 22
    assert net_summary["total_network_dtc_alerts"] == 3


def test_apply_delta_to_snapshot(mock_clickhouse_manager):
    manager, client = mock_clickhouse_manager
    repo = AnalyticsRepository(manager=manager)

    tenant_id = uuid4()
    branch_id = uuid4()
    today = date(2026, 10, 31)

    # Empty existing snapshot -> initializes from delta
    empty_result = MagicMock()
    empty_result.result_rows = []
    client.query.return_value = empty_result

    repo.apply_delta_to_snapshot(
        tenant_id=tenant_id,
        branch_id=branch_id,
        snapshot_date=today,
        revenue_delta=350.0,
        completed_wo_delta=1,
        appointments_delta=2,
        dtc_alerts_delta=1,
    )
    client.insert.assert_called()
    inserted_rows = client.insert.call_args[0][1]
    assert inserted_rows[0][4] == 350.0  # total_revenue
    assert inserted_rows[0][5] == 1  # completed_work_orders_count
    assert inserted_rows[0][6] == 2  # total_appointments_count
    assert inserted_rows[0][8] == 1  # dtc_alerts_count

