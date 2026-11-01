from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Service info
    SERVICE_NAME: str = "erp-analytics-service"
    ENVIRONMENT: str = "development"
    PORT: int = 8090
    HOST: str = "0.0.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ClickHouse OLAP configuration
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DATABASE: str = "driveos_analytics"
    CLICKHOUSE_SECURE: bool = False

    # Kafka consumer configuration
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_GROUP_ID: str = "erp-analytics-group"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_TOPIC_INVOICES: str = "billing.invoices"
    KAFKA_TOPIC_PAYMENTS: str = "billing.payments"
    KAFKA_TOPIC_WORK_ORDERS: str = "workshop.work-orders"
    KAFKA_TOPIC_STOCK_MOVEMENTS: str = "inventory.movements"
    KAFKA_TOPIC_IOT_ALERTS: str = "iot.alerts"
    KAFKA_TOPIC_APPOINTMENTS: str = "fleet.appointments"
    KAFKA_CONSUMER_ENABLED: bool = True

    # Business timezone
    ANALYTICS_ZONE_ID: str = "America/Lima"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def kafka_topics(self) -> List[str]:
        return [
            self.KAFKA_TOPIC_INVOICES,
            self.KAFKA_TOPIC_PAYMENTS,
            self.KAFKA_TOPIC_WORK_ORDERS,
            self.KAFKA_TOPIC_STOCK_MOVEMENTS,
            self.KAFKA_TOPIC_IOT_ALERTS,
            self.KAFKA_TOPIC_APPOINTMENTS,
        ]


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
