from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI

from app.consumers.event_consumer import AnalyticsEventConsumer, KafkaConsumerWorker
from app.core.clickhouse import clickhouse_manager
from app.core.config import get_settings
from app.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and graceful shutdown for ClickHouse and Kafka worker."""
    settings = get_settings()
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.PORT} ({settings.ENVIRONMENT})...")

    # 1. Initialize ClickHouse schema if available
    try:
        clickhouse_manager.init_schema()
        logger.info("ClickHouse schema verified/initialized successfully.")
    except Exception as e:
        logger.warning(f"ClickHouse schema initialization deferred (connection pending): {e}")

    # 2. Initialize repositories, consumer handler, and Kafka worker
    analytics_repo = AnalyticsRepository(manager=clickhouse_manager)
    event_consumer = AnalyticsEventConsumer(repository=analytics_repo)
    kafka_worker = KafkaConsumerWorker(
        event_consumer=event_consumer,
        settings=settings,
    )

    # 3. Start background Kafka consumer
    try:
        await kafka_worker.start()
    except Exception as e:
        logger.warning(f"Kafka consumer start deferred (broker unreachable): {e}")

    # Store objects on application state for dependency injection
    app.state.clickhouse_manager = clickhouse_manager
    app.state.analytics_repo = analytics_repo
    app.state.event_consumer = event_consumer
    app.state.kafka_worker = kafka_worker

    yield

    # Graceful Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME} resources...")
    try:
        await kafka_worker.stop()
    except Exception as e:
        logger.error(f"Error stopping Kafka worker during shutdown: {e}")

    try:
        clickhouse_manager.close()
        logger.info("ClickHouse client disconnected.")
    except Exception as e:
        logger.error(f"Error closing ClickHouse client: {e}")

    logger.info(f"{settings.SERVICE_NAME} shutdown complete.")
