import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from aiokafka import AIOKafkaConsumer

from app.core.config import Settings, get_settings
from app.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)


def parse_datetime(val: Any) -> datetime:
    """Parses ISO string or returns datetime object."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.now(timezone.utc)


class AnalyticsEventConsumer:
    """Processes incoming domain events and routes them to ClickHouse analytics tables."""

    def __init__(self, repository: AnalyticsRepository):
        self._repo = repository

    def process_event_payload(self, topic: str, data: Dict[str, Any]) -> bool:
        """Parses and ingests a domain event payload based on topic and event type."""
        try:
            event_id = UUID(str(data.get("event_id", uuid4())))
            tenant_id = UUID(str(data["tenant_id"]))
            occurred_at = parse_datetime(data.get("occurred_at") or data.get("timestamp"))

            payload = data.get("payload", data)

            if "invoices" in topic:
                self._handle_invoice(event_id, tenant_id, payload, occurred_at)
            elif "payments" in topic:
                self._handle_payment(event_id, tenant_id, payload, occurred_at)
            elif "work-orders" in topic:
                self._handle_work_order(event_id, tenant_id, payload, occurred_at)
            elif "movements" in topic:
                self._handle_stock_movement(event_id, tenant_id, payload, occurred_at)
            elif "alerts" in topic:
                self._handle_telemetry_alert(event_id, tenant_id, payload, occurred_at)
            else:
                logger.debug(f"Unhandled topic in analytics consumer: {topic}")
                return False

            return True
        except KeyError as e:
            logger.error(f"Missing mandatory field in event for topic {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing event for topic {topic}: {e}", exc_info=True)
            return False

    def _handle_invoice(self, event_id: UUID, tenant_id: UUID, p: Dict[str, Any], dt: datetime) -> None:
        record = {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "invoice_id": UUID(str(p.get("invoice_id", uuid4()))),
            "work_order_id": UUID(str(p["work_order_id"])) if p.get("work_order_id") else None,
            "customer_id": UUID(str(p.get("customer_id", uuid4()))),
            "total_amount": float(p.get("total_amount", 0.0)),
            "subtotal": float(p.get("subtotal", 0.0)),
            "tax_amount": float(p.get("tax_amount", 0.0)),
            "parts_cost": float(p.get("parts_cost", 0.0)),
            "labor_cost": float(p.get("labor_cost", 0.0)),
            "status": str(p.get("status", "ISSUED")),
            "issued_at": parse_datetime(p.get("issued_at") or dt),
            "event_date": parse_datetime(p.get("issued_at") or dt).date(),
        }
        self._repo.insert_invoices([record])

    def _handle_payment(self, event_id: UUID, tenant_id: UUID, p: Dict[str, Any], dt: datetime) -> None:
        record = {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "payment_id": UUID(str(p.get("payment_id", uuid4()))),
            "invoice_id": UUID(str(p.get("invoice_id", uuid4()))),
            "amount": float(p.get("amount", 0.0)),
            "payment_method": str(p.get("payment_method", "CREDIT_CARD")),
            "status": str(p.get("status", "COMPLETED")),
            "paid_at": parse_datetime(p.get("paid_at") or dt),
            "event_date": parse_datetime(p.get("paid_at") or dt).date(),
        }
        self._repo.insert_payments([record])

    def _handle_work_order(self, event_id: UUID, tenant_id: UUID, p: Dict[str, Any], dt: datetime) -> None:
        completed_at = parse_datetime(p["completed_at"]) if p.get("completed_at") else (dt if p.get("is_completed") else None)
        record = {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "work_order_id": UUID(str(p.get("work_order_id", uuid4()))),
            "vehicle_id": UUID(str(p.get("vehicle_id", uuid4()))),
            "technician_id": UUID(str(p["technician_id"])) if p.get("technician_id") else None,
            "status": str(p.get("status", "COMPLETED")),
            "cycle_time_hours": float(p.get("cycle_time_hours", 0.0)),
            "lead_time_hours": float(p.get("lead_time_hours", 0.0)),
            "is_completed": 1 if p.get("is_completed", True) else 0,
            "completed_on_time": 1 if p.get("completed_on_time", True) else 0,
            "labor_cost": float(p.get("labor_cost", 0.0)),
            "parts_cost": float(p.get("parts_cost", 0.0)),
            "completed_at": completed_at,
            "event_date": (completed_at.date() if completed_at else dt.date()),
        }
        self._repo.insert_work_orders([record])

    def _handle_stock_movement(self, event_id: UUID, tenant_id: UUID, p: Dict[str, Any], dt: datetime) -> None:
        moved_at = parse_datetime(p.get("moved_at") or dt)
        quantity = int(p.get("quantity", 1))
        unit_cost = float(p.get("unit_cost", 0.0))
        total_cost = float(p.get("total_cost", quantity * unit_cost))
        record = {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "movement_id": UUID(str(p.get("movement_id", uuid4()))),
            "part_id": UUID(str(p.get("part_id", uuid4()))),
            "quantity": quantity,
            "unit_cost": unit_cost,
            "total_cost": total_cost,
            "movement_type": str(p.get("movement_type", "OUT")),
            "moved_at": moved_at,
            "event_date": moved_at.date(),
        }
        self._repo.insert_stock_movements([record])

    def _handle_telemetry_alert(self, event_id: UUID, tenant_id: UUID, p: Dict[str, Any], dt: datetime) -> None:
        alert_timestamp = parse_datetime(p.get("alert_timestamp") or dt)
        record = {
            "event_id": event_id,
            "tenant_id": tenant_id,
            "vehicle_id": UUID(str(p.get("vehicle_id", uuid4()))),
            "device_id": str(p.get("device_id", "")),
            "alert_type": str(p.get("alert_type", "ANOMALY")),
            "severity": str(p.get("severity", "WARNING")),
            "dtc_code": str(p.get("dtc_code", "")),
            "description": str(p.get("description", "")),
            "alert_timestamp": alert_timestamp,
            "event_date": alert_timestamp.date(),
        }
        self._repo.insert_telemetry_alerts([record])


class KafkaConsumerWorker:
    """Background Kafka consumer polling subscribed topics."""

    def __init__(
        self,
        event_consumer: AnalyticsEventConsumer,
        settings: Optional[Settings] = None,
        consumer: Optional[AIOKafkaConsumer] = None,
    ):
        self._handler = event_consumer
        self._settings = settings or get_settings()
        self._consumer = consumer
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Starts Kafka consumer and spawning background polling task."""
        if not self._settings.KAFKA_CONSUMER_ENABLED:
            logger.info("Kafka consumer is disabled via configuration.")
            return

        if self._consumer is None:
            self._consumer = AIOKafkaConsumer(
                *self._settings.kafka_topics,
                bootstrap_servers=self._settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self._settings.KAFKA_GROUP_ID,
                auto_offset_reset=self._settings.KAFKA_AUTO_OFFSET_RESET,
                enable_auto_commit=True,
            )

        await self._consumer.start()
        self._running = True
        logger.info(f"Kafka consumer started on topics: {self._settings.kafka_topics}")
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        """Gracefully halts consumer loop and disconnects client."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._consumer:
            try:
                await self._consumer.stop()
            except Exception as e:
                logger.warning(f"Error disconnecting Kafka consumer: {e}")

        logger.info("Kafka consumer stopped gracefully.")

    async def _consume_loop(self) -> None:
        """Continuous consumption loop deserializing and routing events."""
        while self._running:
            try:
                if not self._consumer:
                    break
                # Poll messages with 1s timeout to allow cancellation
                data = await self._consumer.getmany(timeout_ms=1000, max_records=100)
                for tp, messages in data.items():
                    for msg in messages:
                        try:
                            payload = json.loads(msg.value.decode("utf-8"))
                            self._handler.process_event_payload(msg.topic, payload)
                        except Exception as e:
                            logger.error(f"Error handling message on {msg.topic}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Kafka consumer loop: {e}", exc_info=True)
                await asyncio.sleep(2.0)
