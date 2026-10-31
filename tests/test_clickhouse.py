from unittest.mock import MagicMock
import pytest
from app.core.clickhouse import ClickHouseManager, TABLE_DEFINITIONS
from app.core.config import Settings


def test_table_definitions_contain_partitioning():
    for ddl in TABLE_DEFINITIONS:
        assert "PARTITION BY (tenant_id, toYYYYMM(event_date))" in ddl
        assert "ReplacingMergeTree" in ddl
        assert "tenant_id UUID" in ddl


def test_clickhouse_manager_init_schema():
    mock_client = MagicMock()
    settings = Settings(CLICKHOUSE_DATABASE="test_analytics")
    manager = ClickHouseManager(settings=settings)
    manager.set_client(mock_client)

    manager.init_schema()

    # Verify CREATE DATABASE was called
    assert mock_client.command.call_count == len(TABLE_DEFINITIONS) + 1
    first_call = mock_client.command.call_args_list[0][0][0]
    assert "CREATE DATABASE IF NOT EXISTS test_analytics" in first_call


def test_clickhouse_manager_close():
    mock_client = MagicMock()
    manager = ClickHouseManager()
    manager.set_client(mock_client)
    manager.close()
    mock_client.close.assert_called_once()
    assert manager._client is None
