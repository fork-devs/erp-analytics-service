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

    # 1. Use existing manager if injected in tests, otherwise global clickhouse_manager
    ch_manager = getattr(app.state, "clickhouse_manager", None) or clickhouse_manager
    app.state.clickhouse_manager = ch_manager

    try:
        ch_manager.init_schema()
        logger.info("ClickHouse schema verified/initialized successfully.")
    except Exception as e:
        logger.warning(f"ClickHouse schema initialization deferred (connection pending): {e}")

    # 2. Use existing repo if injected in tests
    analytics_repo = getattr(app.state, "analytics_repo", None) or AnalyticsRepository(manager=ch_manager)
    app.state.analytics_repo = analytics_repo

    event_consumer = getattr(app.state, "event_consumer", None) or AnalyticsEventConsumer(repository=analytics_repo)
    app.state.event_consumer = event_consumer

    kafka_worker = getattr(app.state, "kafka_worker", None) or KafkaConsumerWorker(
        event_consumer=event_consumer,
        settings=settings,
    )
    app.state.kafka_worker = kafka_worker

    # 3. Start background Kafka consumer
    try:
        await kafka_worker.start()
    except Exception as e:
        logger.warning(f"Kafka consumer start deferred (broker unreachable): {e}")

    yield

    # Graceful Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME} resources...")
    try:
        await kafka_worker.stop()
    except Exception as e:
        logger.error(f"Error stopping Kafka worker during shutdown: {e}")

    try:
        ch_manager.close()
        logger.info("ClickHouse client disconnected.")
    except Exception as e:
        logger.error(f"Error closing ClickHouse client: {e}")

    logger.info(f"{settings.SERVICE_NAME} shutdown complete.")
