from typing import Any, List, Optional
import logging
import clickhouse_connect
from clickhouse_connect.driver.client import Client

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# ClickHouse DDL statements
TABLE_DEFINITIONS: List[str] = [
    """
    CREATE TABLE IF NOT EXISTS analytics_invoices (
        event_id UUID,
        tenant_id UUID,
        invoice_id UUID,
        work_order_id Nullable(UUID),
        customer_id UUID,
        total_amount Decimal(12, 2),
        subtotal Decimal(12, 2),
        tax_amount Decimal(12, 2),
        parts_cost Decimal(12, 2),
        labor_cost Decimal(12, 2),
        status LowCardinality(String),
        issued_at DateTime,
        event_date Date DEFAULT toDate(issued_at),
        created_at DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY (tenant_id, toYYYYMM(event_date))
    ORDER BY (tenant_id, event_date, invoice_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_payments (
        event_id UUID,
        tenant_id UUID,
        payment_id UUID,
        invoice_id UUID,
        amount Decimal(12, 2),
        payment_method LowCardinality(String),
        status LowCardinality(String),
        paid_at DateTime,
        event_date Date DEFAULT toDate(paid_at),
        created_at DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY (tenant_id, toYYYYMM(event_date))
    ORDER BY (tenant_id, event_date, payment_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_work_orders (
        event_id UUID,
        tenant_id UUID,
        work_order_id UUID,
        vehicle_id UUID,
        technician_id Nullable(UUID),
        status LowCardinality(String),
        cycle_time_hours Float32,
        lead_time_hours Float32,
        is_completed UInt8,
        completed_on_time UInt8,
        labor_cost Decimal(12, 2),
        parts_cost Decimal(12, 2),
        completed_at Nullable(DateTime),
        event_date Date,
        created_at DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY (tenant_id, toYYYYMM(event_date))
    ORDER BY (tenant_id, event_date, work_order_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_stock_movements (
        event_id UUID,
        tenant_id UUID,
        movement_id UUID,
        part_id UUID,
        quantity Int32,
        unit_cost Decimal(12, 2),
        total_cost Decimal(12, 2),
        movement_type LowCardinality(String),
        moved_at DateTime,
        event_date Date DEFAULT toDate(moved_at),
        created_at DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY (tenant_id, toYYYYMM(event_date))
    ORDER BY (tenant_id, event_date, movement_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_telemetry_alerts (
        event_id UUID,
        tenant_id UUID,
        vehicle_id UUID,
        device_id String,
        alert_type LowCardinality(String),
        severity LowCardinality(String),
        dtc_code String,
        description String,
        alert_timestamp DateTime,
        event_date Date DEFAULT toDate(alert_timestamp),
        created_at DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY (tenant_id, toYYYYMM(event_date))
    ORDER BY (tenant_id, event_date, event_id);
    """
]


class ClickHouseManager:
    """Manages ClickHouse client instance and schema lifecycle."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self._client: Optional[Client] = None

    def get_client(self) -> Client:
        """Returns or establishes the ClickHouse client."""
        if self._client is None:
            self._client = clickhouse_connect.get_client(
                host=self._settings.CLICKHOUSE_HOST,
                port=self._settings.CLICKHOUSE_PORT,
                username=self._settings.CLICKHOUSE_USER,
                password=self._settings.CLICKHOUSE_PASSWORD,
                database=self._settings.CLICKHOUSE_DATABASE,
                secure=self._settings.CLICKHOUSE_SECURE,
            )
        return self._client

    def set_client(self, client: Client) -> None:
        """Sets client explicitly, useful for mocking in test environments."""
        self._client = client

    def close(self) -> None:
        """Closes active client connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                logger.warning("Error closing ClickHouse connection: %s", e)
            self._client = None

    def init_schema(self) -> None:
        """Initializes database and analytics tables in ClickHouse."""
        client = self.get_client()
        # Ensure target database exists
        client.command(f"CREATE DATABASE IF NOT EXISTS {self._settings.CLICKHOUSE_DATABASE}")
        for ddl in TABLE_DEFINITIONS:
            client.command(ddl.strip())
        logger.info("ClickHouse schema initialized successfully.")


# Global singleton instance
clickhouse_manager = ClickHouseManager()
