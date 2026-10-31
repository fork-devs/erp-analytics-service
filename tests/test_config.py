import os
import pytest
from app.core.config import Settings, get_settings


def test_default_settings():
    settings = Settings(_env_file=None)
    assert settings.SERVICE_NAME == "erp-analytics-service"
    assert settings.PORT == 8090
    assert settings.CLICKHOUSE_PORT == 8123
    assert settings.CLICKHOUSE_DATABASE == "driveos_analytics"
    assert "billing.invoices" in settings.kafka_topics
    assert "iot.alerts" in settings.kafka_topics


def test_custom_environment_settings(monkeypatch):
    monkeypatch.setenv("PORT", "9099")
    monkeypatch.setenv("CLICKHOUSE_HOST", "clickhouse.prod.internal")
    monkeypatch.setenv("ENVIRONMENT", "production")

    custom_settings = Settings(_env_file=None)
    assert custom_settings.PORT == 9099
    assert custom_settings.CLICKHOUSE_HOST == "clickhouse.prod.internal"
    assert custom_settings.ENVIRONMENT == "production"


def test_get_settings_singleton():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
