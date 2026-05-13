"""Redis Streams consumer for aggregation commands."""

from __future__ import annotations

import json
import logging
import threading
import time
import traceback
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis

from config import (
    AGGREGATION_COMMAND_CONSUMER_GROUP,
    AGGREGATION_COMMAND_CONSUMER_NAME,
    AGGREGATION_COMMAND_STREAM,
    AGGREGATION_RESULT_TTL_SECONDS,
    ENABLE_REDIS_COMMAND_CONSUMER,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
)
from services.commands import AggregationCommandHandler

logger = logging.getLogger(__name__)


class AggregationRedisConsumer:
    def __init__(self, handler: AggregationCommandHandler | None = None, redis_client=None):
        self.handler = handler or AggregationCommandHandler()
        self.redis = redis_client or redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            db=REDIS_DB,
            decode_responses=True,
            socket_timeout=10,
            socket_connect_timeout=5,
        )
        self.stream = AGGREGATION_COMMAND_STREAM
        self.group = AGGREGATION_COMMAND_CONSUMER_GROUP
        self.consumer_name = AGGREGATION_COMMAND_CONSUMER_NAME or f"aggregation-{uuid4().hex[:8]}"
        self.result_ttl_seconds = AGGREGATION_RESULT_TTL_SECONDS
        self._stop_event = threading.Event()

    def start_forever(self) -> None:
        self.ensure_group()
        logger.info(
            "aggregation Redis consumer started stream=%s group=%s consumer=%s",
            self.stream,
            self.group,
            self.consumer_name,
        )
        while not self._stop_event.is_set():
            try:
                self.consume_once(block_ms=5000, count=1)
            except Exception as exc:
                logger.error("aggregation Redis consumer loop error: %s", exc, exc_info=True)
                time.sleep(3)

    def stop(self) -> None:
        self._stop_event.set()

    def ensure_group(self) -> None:
        try:
            self.redis.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def consume_once(self, block_ms: int = 1000, count: int = 1) -> int:
        messages = self.redis.xreadgroup(
            self.group,
            self.consumer_name,
            {self.stream: ">"},
            count=count,
            block=block_ms,
        )
        processed = 0
        for _, entries in messages:
            for message_id, fields in entries:
                self._handle_message(message_id, fields)
                processed += 1
        return processed

    def _handle_message(self, message_id: str, fields: dict[str, str]) -> None:
        request_id = fields.get("request_id") or message_id
        action = fields.get("action", "")
        logger.info("收到聚合命令 request_id=%s action=%s message_id=%s", request_id, action, message_id)
        started_at = datetime.now()
        try:
            payload = _decode_payload(fields.get("payload"))
            data = self.handler.handle(action, payload)
            result = {
                "request_id": request_id,
                "action": action,
                "status": "succeeded",
                "message": "success",
                "data": data,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now().isoformat(),
            }
            self._store_result(request_id, result)
            self.redis.xack(self.stream, self.group, message_id)
            logger.info("聚合命令执行成功 request_id=%s action=%s", request_id, action)
        except Exception as exc:
            result = {
                "request_id": request_id,
                "action": action,
                "status": "failed",
                "message": str(exc),
                "data": {},
                "error": traceback.format_exc(limit=8),
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now().isoformat(),
            }
            self._store_result(request_id, result)
            self.redis.xack(self.stream, self.group, message_id)
            logger.error("聚合命令执行失败 request_id=%s action=%s error=%s", request_id, action, exc, exc_info=True)

    def _store_result(self, request_id: str, result: dict[str, Any]) -> None:
        key = result_key(request_id)
        self.redis.setex(key, self.result_ttl_seconds, json.dumps(result, ensure_ascii=False, default=str))


def result_key(request_id: str) -> str:
    return f"info_ai:aggregation:results:{request_id}"


def _decode_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if isinstance(value, dict):
        return value
    raise ValueError("payload must be a JSON object")


def start_aggregation_consumer() -> AggregationRedisConsumer | None:
    if not ENABLE_REDIS_COMMAND_CONSUMER:
        logger.info("aggregation Redis consumer disabled")
        return None
    consumer = AggregationRedisConsumer()
    thread = threading.Thread(target=consumer.start_forever, name="aggregation-redis-consumer", daemon=True)
    thread.start()
    return consumer
