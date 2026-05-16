import json

from services.messaging.redis_consumer import AggregationRedisConsumer, result_key


class FakeHandler:
    def __init__(self):
        self.calls = []

    def handle(self, action, payload):
        self.calls.append((action, payload))
        return {"handled": action}


class FakeRedis:
    def __init__(self, new_messages=None, claimed_messages=None):
        self.new_messages = new_messages or []
        self.claimed_messages = claimed_messages or []
        self.setex_calls = []
        self.acked = []
        self.xreadgroup_calls = []
        self.xautoclaim_calls = []

    def xreadgroup(self, group, consumer, streams, count=None, block=None):
        self.xreadgroup_calls.append(
            {"group": group, "consumer": consumer, "streams": streams, "count": count, "block": block}
        )
        return [(next(iter(streams)), self.new_messages)] if self.new_messages else []

    def xautoclaim(self, stream, group, consumer, min_idle_time, start_id="0-0", count=None, justid=False):
        self.xautoclaim_calls.append(
            {
                "stream": stream,
                "group": group,
                "consumer": consumer,
                "min_idle_time": min_idle_time,
                "start_id": start_id,
                "count": count,
                "justid": justid,
            }
        )
        return ("0-0", self.claimed_messages, [])

    def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))

    def xack(self, stream, group, message_id):
        self.acked.append((stream, group, message_id))


def test_result_key_uses_configurable_prefix():
    assert result_key("req-1", "custom:results:") == "custom:results:req-1"


def test_consume_once_stores_result_with_configurable_prefix():
    redis = FakeRedis(
        new_messages=[
            (
                "1-0",
                {
                    "request_id": "req-1",
                    "action": "refresh_quality",
                    "payload": json.dumps({"category_code": "hot"}),
                },
            )
        ]
    )
    handler = FakeHandler()
    consumer = AggregationRedisConsumer(handler=handler, redis_client=redis)
    consumer.result_prefix = "custom:results:"

    assert consumer.consume_once(block_ms=1, count=1) == 1

    assert handler.calls == [("refresh_quality", {"category_code": "hot"})]
    assert redis.setex_calls[0][0] == "custom:results:req-1"
    assert redis.acked == [(consumer.stream, consumer.group, "1-0")]


def test_consume_once_claims_stale_pending_before_new_messages():
    redis = FakeRedis(
        new_messages=[("2-0", {"request_id": "new", "action": "noop", "payload": "{}"})],
        claimed_messages=[("1-0", {"request_id": "pending", "action": "noop", "payload": "{}"})],
    )
    handler = FakeHandler()
    consumer = AggregationRedisConsumer(handler=handler, redis_client=redis)
    consumer.pending_idle_ms = 12345

    assert consumer.consume_once(block_ms=1, count=1) == 1

    assert handler.calls == [("noop", {})]
    assert redis.xautoclaim_calls[0]["min_idle_time"] == 12345
    assert redis.xreadgroup_calls == []
    assert redis.acked == [(consumer.stream, consumer.group, "1-0")]
