from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from starlette.testclient import TestClient
from app.core.lifespan import lifespan
from app.main import app


@pytest.mark.asyncio
async def test_lifespan_context_manager():
    with patch("app.core.lifespan.clickhouse_manager") as mock_ch, \
         patch("app.core.lifespan.KafkaConsumerWorker") as mock_worker_cls:

        mock_worker = MagicMock()
        mock_worker.start = AsyncMock()
        mock_worker.stop = AsyncMock()
        mock_worker_cls.return_value = mock_worker

        dummy_app = MagicMock()
        dummy_app.state = MagicMock()

        async with lifespan(dummy_app):
            mock_worker.start.assert_awaited_once()
            assert dummy_app.state.kafka_worker == mock_worker

        mock_worker.stop.assert_awaited_once()
        mock_ch.close.assert_called_once()


def test_main_root_endpoint():
    with patch("app.core.lifespan.clickhouse_manager"), \
         patch("app.core.lifespan.KafkaConsumerWorker") as mock_worker_cls:
        mock_worker = MagicMock()
        mock_worker.start = AsyncMock()
        mock_worker.stop = AsyncMock()
        mock_worker_cls.return_value = mock_worker

        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "erp-analytics-service"
            assert data["docs"] == "/docs"
