"""Event bus abstractions for market event ingest."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from rada.schemas import MarketEvent

logger = logging.getLogger(__name__)


class BaseEventBus(ABC):
    """Async queue abstraction for MarketEvent ingest."""

    @abstractmethod
    async def enqueue(self, event: MarketEvent) -> None:
        """Publish one market event."""

    @abstractmethod
    async def dequeue(self) -> MarketEvent:
        """Block until one market event is available."""

    async def close(self) -> None:
        """Release backend resources when supported."""


class InMemoryEventBus(BaseEventBus):
    def __init__(self) -> None:
        self._queue: asyncio.Queue[MarketEvent] = asyncio.Queue()

    async def enqueue(self, event: MarketEvent) -> None:
        await self._queue.put(event)

    async def dequeue(self) -> MarketEvent:
        return await self._queue.get()


class RedisEventBus(BaseEventBus):
    """Redis list-backed bus (same channel semantics as bootstrap main)."""

    def __init__(self, redis_url: str, *, channel: str = "rada:events") -> None:
        import redis.asyncio as redis

        self._channel = channel
        self._client = redis.from_url(redis_url)

    async def enqueue(self, event: MarketEvent) -> None:
        await self._client.rpush(self._channel, event.model_dump_json())

    async def dequeue(self) -> MarketEvent:
        _, payload = await self._client.blpop(self._channel)
        return MarketEvent.model_validate_json(payload)

    async def close(self) -> None:
        await self._client.aclose()


class KafkaEventBus(BaseEventBus):
    """Kafka-backed bus using aiokafka when installed; falls back to in-memory."""

    def __init__(
        self,
        bootstrap_servers: str,
        *,
        topic: str = "rada.events",
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._topic = topic
        self._fallback = InMemoryEventBus()
        self._producer = None
        self._consumer = None
        self._use_kafka = False

        try:
            from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

            self._producer_cls = AIOKafkaProducer
            self._consumer_cls = AIOKafkaConsumer
            self._use_kafka = True
        except ImportError:
            logger.warning("aiokafka not installed; KafkaEventBus uses in-memory fallback")
            self._use_kafka = False

    async def _ensure_kafka(self) -> None:
        if not self._use_kafka or self._producer is not None:
            return
        self._producer = self._producer_cls(bootstrap_servers=self._bootstrap)
        self._consumer = self._consumer_cls(
            self._topic,
            bootstrap_servers=self._bootstrap,
            group_id="rada-ingest",
            auto_offset_reset="earliest",
        )
        await self._producer.start()
        await self._consumer.start()

    async def enqueue(self, event: MarketEvent) -> None:
        if not self._use_kafka:
            await self._fallback.enqueue(event)
            return
        await self._ensure_kafka()
        payload = event.model_dump_json().encode()
        await self._producer.send_and_wait(self._topic, payload)

    async def dequeue(self) -> MarketEvent:
        if not self._use_kafka:
            return await self._fallback.dequeue()
        await self._ensure_kafka()
        msg = await self._consumer.getone()
        return MarketEvent.model_validate_json(msg.value.decode())

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None


class ZeroMQEventBus(BaseEventBus):
    """ZeroMQ PUB/SUB bus; local dequeue only (cross-process subscribe not implemented)."""

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self._fallback = InMemoryEventBus()
        self._pub = None
        self._sub = None
        self._use_zmq = False
        self._local_queue: asyncio.Queue[MarketEvent] = asyncio.Queue()

        try:
            import zmq
            import zmq.asyncio

            self._zmq = zmq
            self._zmq_asyncio = zmq.asyncio
            self._use_zmq = True
        except ImportError:
            logger.warning("pyzmq not installed; ZeroMQEventBus uses in-memory fallback")
            self._use_zmq = False

    async def _ensure_zmq(self) -> None:
        if not self._use_zmq or self._pub is not None:
            return
        ctx = self._zmq_asyncio.Context()
        self._pub = ctx.socket(self._zmq.PUB)
        self._sub = ctx.socket(self._zmq.SUB)
        self._pub.bind(self._endpoint)
        self._sub.connect(self._endpoint)
        self._sub.setsockopt_string(self._zmq.SUBSCRIBE, "rada")

    async def enqueue(self, event: MarketEvent) -> None:
        if not self._use_zmq:
            await self._fallback.enqueue(event)
            return
        await self._ensure_zmq()
        frame = json.dumps({"topic": "rada", "event": event.model_dump(mode="json")})
        await self._pub.send_string(frame)
        await self._local_queue.put(event)

    async def dequeue(self) -> MarketEvent:
        if not self._use_zmq:
            return await self._fallback.dequeue()
        return await self._local_queue.get()


async def build_event_bus(mode: str | None = None) -> BaseEventBus:
    """Factory for configured event bus backend."""
    selected = (mode or os.getenv("RADA_EVENT_BUS_MODE", "inmemory")).lower()

    if selected == "redis":
        redis_url = os.getenv("RADA_REDIS_URL", "redis://localhost:6379/0")
        try:
            return RedisEventBus(redis_url)
        except Exception:
            logger.exception(
                "failed to initialize RedisEventBus for %s; falling back to in-memory",
                redis_url,
            )
            return InMemoryEventBus()

    if selected == "kafka":
        bootstrap = os.getenv("RADA_KAFKA_BOOTSTRAP", "localhost:9092")
        return KafkaEventBus(bootstrap)

    if selected == "zeromq":
        endpoint = os.getenv("RADA_ZMQ_ENDPOINT", "tcp://127.0.0.1:5555")
        return ZeroMQEventBus(endpoint)

    return InMemoryEventBus()


async def drain_events(bus: BaseEventBus, *, max_events: int) -> AsyncIterator[MarketEvent]:
    """Yield up to max_events from bus (non-blocking batch helper for tests)."""
    for _ in range(max_events):
        try:
            event = await asyncio.wait_for(bus.dequeue(), timeout=0.1)
        except TimeoutError:
            break
        yield event
