"""Unit tests for async I/O flow support"""
import asyncio
import pytest
from datetime import datetime

from sub_pub.core.interfaces import AsyncMessageSource, AsyncMessagePublisher
from sub_pub.core.message import Message
from sub_pub.domain.processor import AsyncMessageProcessor, AsyncPassThroughProcessor
from sub_pub.adapters.mock import AsyncMockSource, AsyncMockPublisher
from sub_pub.flows.async_base import AsyncFlow
from sub_pub.flows.async_one_to_one import AsyncOneToOneFlow
from sub_pub.config.models import (
    ThreadPoolConfig,
    BackPressureConfig,
    OneToOneMapping,
)


def _make_message(topic: str, payload: str, index: int = 1) -> Message:
    return Message(
        payload=payload.encode("utf-8"),
        headers={"idx": str(index)},
        topic=topic,
        key=f"key-{index}",
        timestamp=datetime.now(),
    )


def _make_flow(messages, mappings):
    """Helper to build an AsyncOneToOneFlow with mock adapters."""
    source = AsyncMockSource(messages=messages)
    publisher = AsyncMockPublisher()
    thread_cfg = ThreadPoolConfig(max_workers=2, queue_size=100)
    bp_cfg = BackPressureConfig(enabled=False)
    flow = AsyncOneToOneFlow(
        source=source,
        destination=publisher,
        mappings=mappings,
        thread_pool_config=thread_cfg,
        back_pressure_config=bp_cfg,
    )
    return flow, source, publisher


class TestAsyncInterfaces:
    def test_async_message_source_is_abstract(self):
        with pytest.raises(TypeError):
            AsyncMessageSource()

    def test_async_message_publisher_is_abstract(self):
        with pytest.raises(TypeError):
            AsyncMessagePublisher()

    def test_async_message_processor_is_abstract(self):
        with pytest.raises(TypeError):
            AsyncMessageProcessor()


class TestAsyncPassThroughProcessor:
    def test_returns_same_message(self):
        msg = _make_message("t", "hello")
        processor = AsyncPassThroughProcessor()
        result = asyncio.run(processor.process(msg))
        assert result is msg


class TestAsyncMockSource:
    def test_connects_and_closes(self):
        async def _run():
            src = AsyncMockSource(messages=[])
            await src.connect()
            assert src._connected
            await src.close()
            assert not src._connected

        asyncio.run(_run())

    def test_subscribe_stores_topics(self):
        async def _run():
            src = AsyncMockSource(messages=[])
            await src.subscribe(["topic-a", "topic-b"])
            assert src.subscribed_topics == ["topic-a", "topic-b"]

        asyncio.run(_run())

    def test_consume_yields_predefined_messages(self):
        msgs = [
            _make_message("t", "msg1", 1),
            _make_message("t", "msg2", 2),
        ]

        async def _run():
            src = AsyncMockSource(messages=msgs)
            src._connected = True
            received = []
            async for m in src.consume():
                received.append(m)
            return received

        result = asyncio.run(_run())
        assert result == msgs

    def test_commit_is_no_op(self):
        async def _run():
            src = AsyncMockSource(messages=[])
            msg = _make_message("t", "x")
            await src.commit(msg)  # should not raise

        asyncio.run(_run())


class TestAsyncMockPublisher:
    def test_connects_and_closes(self):
        async def _run():
            pub = AsyncMockPublisher()
            await pub.connect()
            assert pub._connected
            await pub.close()
            assert not pub._connected

        asyncio.run(_run())

    def test_publish_stores_messages(self):
        async def _run():
            pub = AsyncMockPublisher()
            msg = _make_message("t", "hello")
            await pub.publish(msg, "dest-topic")
            assert len(pub.published_messages) == 1
            assert pub.published_messages[0] == (msg, "dest-topic")

        asyncio.run(_run())

    def test_flush_does_not_raise(self):
        async def _run():
            pub = AsyncMockPublisher()
            await pub.flush()

        asyncio.run(_run())


class TestAsyncOneToOneFlow:
    def test_routes_messages_to_correct_topics(self):
        msgs = [
            _make_message("src-a", "hello-a", 1),
            _make_message("src-b", "hello-b", 2),
        ]
        mappings = [
            OneToOneMapping(source_topic="src-a", destination_topic="dst-a"),
            OneToOneMapping(source_topic="src-b", destination_topic="dst-b"),
        ]
        flow, source, publisher = _make_flow(msgs, mappings)

        async def _run():
            task = asyncio.create_task(flow.run())
            # Allow the flow to process messages
            await asyncio.sleep(0.2)
            await flow.shutdown()
            await task

        asyncio.run(_run())

        dest_topics = {topic for _, topic in publisher.published_messages}
        assert "dst-a" in dest_topics
        assert "dst-b" in dest_topics
        assert len(publisher.published_messages) == 2

    def test_skips_messages_without_mapping(self):
        msgs = [_make_message("unmapped-topic", "data", 1)]
        mappings = [OneToOneMapping(source_topic="src-x", destination_topic="dst-x")]
        flow, source, publisher = _make_flow(msgs, mappings)

        async def _run():
            task = asyncio.create_task(flow.run())
            await asyncio.sleep(0.2)
            await flow.shutdown()
            await task

        asyncio.run(_run())

        assert len(publisher.published_messages) == 0

    def test_metrics_recorded_for_source_and_destination(self):
        msgs = [_make_message("src-a", "payload", 1)]
        mappings = [OneToOneMapping(source_topic="src-a", destination_topic="dst-a")]
        flow, source, publisher = _make_flow(msgs, mappings)

        async def _run():
            task = asyncio.create_task(flow.run())
            await asyncio.sleep(0.2)
            await flow.shutdown()
            await task

        asyncio.run(_run())

        metrics = flow.metrics.get_metrics()
        assert "src-a" in metrics["source_metrics"]
        assert "dst-a" in metrics["destination_metrics"]

    def test_shutdown_drains_queues(self):
        """Shutdown should complete without hanging."""
        msgs = [_make_message("src-a", f"msg-{i}", i) for i in range(5)]
        mappings = [OneToOneMapping(source_topic="src-a", destination_topic="dst-a")]
        flow, source, publisher = _make_flow(msgs, mappings)

        async def _run():
            task = asyncio.create_task(flow.run())
            await asyncio.sleep(0.3)
            await flow.shutdown()
            await asyncio.wait_for(task, timeout=2.0)

        asyncio.run(_run())
