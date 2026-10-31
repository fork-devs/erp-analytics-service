from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest

from app.consumers.event_consumer import AnalyticsEventConsumer, KafkaConsumerWorker, parse_datetime
from app.core.config import Settings


@pytest.fixture
def mock_repo():
    return MagicMock()


def test_parse_datetime():
    dt = datetime.now(timezone.utc)
    assert parse_datetime(dt) == dt
    iso_str = "2026-10-30T15:30:00Z"
    parsed = parse_datetime(iso_str)
    assert parsed.year == 2026 and parsed.month == 10
    invalid_parsed = parse_datetime("invalid-date")
    assert isinstance(invalid_parsed, datetime)


def test_process_invoice_event(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    tenant_id = uuid4()
    payload = {
        "event_id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-30T12:00:00Z",
        "payload": {
            "invoice_id": str(uuid4()),
            "total_amount": 1250.0,
            "parts_cost": 450.0,
            "labor_cost": 300.0,
            "status": "ISSUED",
        },
    }

    result = consumer.process_event_payload("billing.invoices", payload)
    assert result is True
    mock_repo.insert_invoices.assert_called_once()
    records = mock_repo.insert_invoices.call_args[0][0]
    assert len(records) == 1
    assert records[0]["total_amount"] == 1250.0
    assert records[0]["tenant_id"] == tenant_id


def test_process_payment_event(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    tenant_id = uuid4()
    payload = {
        "event_id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-30T12:00:00Z",
        "payload": {
            "payment_id": str(uuid4()),
            "invoice_id": str(uuid4()),
            "amount": 1250.0,
            "payment_method": "CREDIT_CARD",
        },
    }

    result = consumer.process_event_payload("billing.payments", payload)
    assert result is True
    mock_repo.insert_payments.assert_called_once()


def test_process_work_order_event(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    tenant_id = uuid4()
    payload = {
        "event_id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-30T12:00:00Z",
        "payload": {
            "work_order_id": str(uuid4()),
            "vehicle_id": str(uuid4()),
            "cycle_time_hours": 3.5,
            "is_completed": True,
            "completed_on_time": True,
        },
    }

    result = consumer.process_event_payload("workshop.work-orders", payload)
    assert result is True
    mock_repo.insert_work_orders.assert_called_once()


def test_process_stock_movement_event(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    tenant_id = uuid4()
    payload = {
        "event_id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-30T12:00:00Z",
        "payload": {
            "movement_id": str(uuid4()),
            "part_id": str(uuid4()),
            "quantity": 4,
            "unit_cost": 25.0,
            "total_cost": 100.0,
        },
    }

    result = consumer.process_event_payload("inventory.movements", payload)
    assert result is True
    mock_repo.insert_stock_movements.assert_called_once()


def test_process_iot_alert_event(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    tenant_id = uuid4()
    payload = {
        "event_id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-30T12:00:00Z",
        "payload": {
            "vehicle_id": str(uuid4()),
            "severity": "CRITICAL",
            "dtc_code": "P0300",
            "description": "Random Misfire",
        },
    }

    result = consumer.process_event_payload("iot.alerts", payload)
    assert result is True
    mock_repo.insert_telemetry_alerts.assert_called_once()


def test_process_missing_tenant_id(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    payload = {"event_id": str(uuid4()), "payload": {}}
    result = consumer.process_event_payload("billing.invoices", payload)
    assert result is False


def test_process_unknown_topic(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    payload = {"tenant_id": str(uuid4()), "event_id": str(uuid4())}
    result = consumer.process_event_payload("unknown.topic", payload)
    assert result is False


@pytest.mark.asyncio
async def test_kafka_worker_lifecycle(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    mock_aiokafka = AsyncMock()
    settings = Settings(KAFKA_CONSUMER_ENABLED=True)

    worker = KafkaConsumerWorker(
        event_consumer=consumer,
        settings=settings,
        consumer=mock_aiokafka,
    )

    await worker.start()
    assert worker._running is True
    mock_aiokafka.start.assert_awaited_once()

    await worker.stop()
    assert worker._running is False
    mock_aiokafka.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_kafka_worker_disabled(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    mock_aiokafka = AsyncMock()
    settings = Settings(KAFKA_CONSUMER_ENABLED=False)

    worker = KafkaConsumerWorker(
        event_consumer=consumer,
        settings=settings,
        consumer=mock_aiokafka,
    )

    await worker.start()
    assert worker._running is False
    mock_aiokafka.start.assert_not_awaited()


def test_process_branch_snapshot_events(mock_repo):
    consumer = AnalyticsEventConsumer(repository=mock_repo)
    tenant_id = uuid4()
    branch_id = uuid4()
    b_date = date(2026, 10, 31)

    # 1. WorkOrderCompleted
    wo_payload = {
        "event_id": str(uuid4()),
        "event_type": "WorkOrderCompleted",
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-31T10:00:00Z",
        "payload": {
            "work_order_id": str(uuid4()),
            "branch_id": str(branch_id),
            "total_amount": 350.0,
            "is_completed": True,
        },
    }
    assert consumer.process_event_payload("workshop.work-orders", wo_payload) is True
    mock_repo.apply_delta_to_snapshot.assert_called_with(
        tenant_id=tenant_id,
        branch_id=branch_id,
        snapshot_date=b_date,
        revenue_delta=350.0,
        completed_wo_delta=1,
    )

    # 2. WorkOrderReopened
    reopen_payload = {
        "event_id": str(uuid4()),
        "event_type": "WorkOrderReopened",
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-31T11:00:00Z",
        "payload": {
            "work_order_id": str(uuid4()),
            "branch_id": str(branch_id),
            "total_amount": 350.0,
        },
    }
    assert consumer.process_event_payload("workshop.work-orders", reopen_payload) is True
    mock_repo.apply_delta_to_snapshot.assert_called_with(
        tenant_id=tenant_id,
        branch_id=branch_id,
        snapshot_date=b_date,
        revenue_delta=-350.0,
        completed_wo_delta=-1,
    )

    # 3. AppointmentCreated
    app_payload = {
        "event_id": str(uuid4()),
        "event_type": "AppointmentCreated",
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-31T12:00:00Z",
        "payload": {
            "appointment_id": str(uuid4()),
            "branch_id": str(branch_id),
        },
    }
    assert consumer.process_event_payload("fleet.appointments", app_payload) is True
    mock_repo.apply_delta_to_snapshot.assert_called_with(
        tenant_id=tenant_id,
        branch_id=branch_id,
        snapshot_date=b_date,
        appointments_delta=1,
    )

    # 4. DtcAlertTriggered
    dtc_payload = {
        "event_id": str(uuid4()),
        "event_type": "DtcAlertTriggered",
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-31T13:00:00Z",
        "payload": {
            "vehicle_id": str(uuid4()),
            "branch_id": str(branch_id),
            "dtc_code": "P0300",
            "severity": "CRITICAL",
        },
    }
    assert consumer.process_event_payload("iot.alerts", dtc_payload) is True
    mock_repo.apply_delta_to_snapshot.assert_called_with(
        tenant_id=tenant_id,
        branch_id=branch_id,
        snapshot_date=b_date,
        dtc_alerts_delta=1,
    )

    # 5. LowStockAlertTriggered
    stock_payload = {
        "event_id": str(uuid4()),
        "event_type": "LowStockAlertTriggered",
        "tenant_id": str(tenant_id),
        "occurred_at": "2026-10-31T14:00:00Z",
        "payload": {
            "branch_id": str(branch_id),
            "low_stock_alerts_count": 3,
        },
    }
    assert consumer.process_event_payload("inventory.alerts", stock_payload) is True
    mock_repo.apply_delta_to_snapshot.assert_called_with(
        tenant_id=tenant_id,
        branch_id=branch_id,
        snapshot_date=b_date,
        low_stock_alerts_count=3,
    )

