"""Unit tests for the Azure Event Hubs adapter (using mocks)."""
import queue
import threading
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch, call

import pytest

from sub_pub.adapters.eventhubs import EventHubsSource, EventHubsPublisher
from sub_pub.core.message import Message


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

def _make_config(extras: Optional[dict] = None) -> dict:
    base = {"connection_string": "Endpoint=sb://fake.servicebus.windows.net/;..."}
    if extras:
        base.update(extras)
    return base


def _make_fake_event(body: bytes, properties: Optional[dict] = None,
                     partition_id: str = "0", offset: str = "42") -> MagicMock:
    """Return a mock EventData-like object."""
    event = MagicMock()
    event.body_as_bytes.return_value = body
    event.properties = properties or {}
    event.offset = offset
    event.enqueued_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return event


def _make_fake_partition_context(partition_id: str = "0") -> MagicMock:
    ctx = MagicMock()
    ctx.partition_id = partition_id
    return ctx


# ---------------------------------------------------------------------------
# EventHubsSource
# ---------------------------------------------------------------------------

class TestEventHubsSourceConnect:
    def test_connect_creates_consumer_client(self):
        mock_client = MagicMock()
        mock_cls = MagicMock()
        mock_cls.from_connection_string.return_value = mock_client

        with patch.dict("sys.modules", {"azure.eventhub": MagicMock(EventHubConsumerClient=mock_cls)}):
            source = EventHubsSource(_make_config())
            source.connect()

        mock_cls.from_connection_string.assert_called_once()
        assert source.client is mock_client

    def test_connect_raises_on_missing_package(self):
        source = EventHubsSource(_make_config())
        with patch.dict("sys.modules", {"azure.eventhub": None}):
            with pytest.raises((ImportError, TypeError)):
                source.connect()

    def test_subscribe_is_no_op(self):
        source = EventHubsSource(_make_config())
        source.client = MagicMock()
        source.subscribe(["topic-a", "topic-b"])  # should not raise


class TestEventHubsSourceConsume:
    def _run_consume(self, source: EventHubsSource, events_to_inject: list,
                     timeout: float = 2.0) -> list:
        """
        Drive consume() by simulating the SDK's receive() callback mechanism:
        a helper thread injects events into the source's _event_queue after
        the receive thread has started.
        """
        received: list[Message] = []

        def _fake_receive(on_event, on_error=None, starting_position=None):
            # Block briefly to let consume() start polling the queue
            threading.Event().wait(0.05)
            for partition_id, event in events_to_inject:
                ctx = _make_fake_partition_context(partition_id)
                on_event(ctx, event)
            # Simulate the receive loop ending (daemon thread exits)

        source.client = MagicMock()
        source.client.receive.side_effect = _fake_receive

        gen = source.consume()
        # Collect up to len(events_to_inject) messages
        for _ in events_to_inject:
            try:
                msg = next(gen)
                received.append(msg)
            except StopIteration:
                break

        return received

    def test_consume_yields_message_for_each_event(self):
        source = EventHubsSource(_make_config())
        events = [
            ("0", _make_fake_event(b"hello")),
            ("1", _make_fake_event(b"world")),
        ]
        messages = self._run_consume(source, events)

        assert len(messages) == 2
        assert messages[0].payload == b"hello"
        assert messages[1].payload == b"world"

    def test_consume_decodes_byte_property_keys_and_values(self):
        source = EventHubsSource(_make_config())
        props = {b"content-type": b"application/json"}
        event = _make_fake_event(b"data", properties=props)
        messages = self._run_consume(source, [("0", event)])

        assert messages[0].headers == {"content-type": "application/json"}

    def test_consume_sets_partition_and_offset(self):
        source = EventHubsSource(_make_config())
        event = _make_fake_event(b"data", partition_id="3", offset="99")
        event.offset = "99"
        messages = self._run_consume(source, [("3", event)])

        assert messages[0].partition == 3
        assert messages[0].offset == "99"

    def test_consume_skips_none_events(self):
        source = EventHubsSource(_make_config())

        def _fake_receive(on_event, on_error=None, starting_position=None):
            threading.Event().wait(0.05)
            ctx = _make_fake_partition_context("0")
            on_event(ctx, None)   # None event – should be skipped
            on_event(ctx, _make_fake_event(b"real"))

        source.client = MagicMock()
        source.client.receive.side_effect = _fake_receive

        gen = source.consume()
        msg = next(gen)
        assert msg.payload == b"real"

    def test_consume_raises_when_not_connected(self):
        source = EventHubsSource(_make_config())
        with pytest.raises(RuntimeError, match="not connected"):
            next(source.consume())


class TestEventHubsSourceCommit:
    def test_commit_calls_update_checkpoint_and_clears_state(self):
        source = EventHubsSource(_make_config())
        ctx0 = _make_fake_partition_context("0")
        ctx1 = _make_fake_partition_context("1")
        event0 = _make_fake_event(b"a")
        event1 = _make_fake_event(b"b")
        source._last_event_per_partition = {
            "0": (ctx0, event0),
            "1": (ctx1, event1),
        }

        source.commit()

        ctx0.update_checkpoint.assert_called_once_with(event0)
        ctx1.update_checkpoint.assert_called_once_with(event1)
        assert source._last_event_per_partition == {}

    def test_commit_tolerates_checkpoint_errors(self):
        source = EventHubsSource(_make_config())
        ctx = _make_fake_partition_context("0")
        ctx.update_checkpoint.side_effect = RuntimeError("network error")
        source._last_event_per_partition = {"0": (ctx, _make_fake_event(b"x"))}

        source.commit()  # should not raise

    def test_commit_is_no_op_when_no_events_received(self):
        source = EventHubsSource(_make_config())
        source.commit()  # should not raise


class TestEventHubsSourceClose:
    def test_close_calls_client_close(self):
        source = EventHubsSource(_make_config())
        source.client = MagicMock()
        source.close()
        source.client.close.assert_called_once()

    def test_close_is_safe_when_not_connected(self):
        source = EventHubsSource(_make_config())
        source.close()  # should not raise


# ---------------------------------------------------------------------------
# EventHubsPublisher
# ---------------------------------------------------------------------------

class TestEventHubsPublisherConnect:
    def test_connect_creates_producer_client(self):
        mock_client = MagicMock()
        mock_cls = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {"azure.eventhub": MagicMock(EventHubProducerClient=mock_cls)}):
            publisher = EventHubsPublisher(_make_config())
            publisher.connect()

        mock_cls.from_connection_string.assert_called_once()

    def test_connect_raises_on_missing_package(self):
        publisher = EventHubsPublisher(_make_config())
        with patch.dict("sys.modules", {"azure.eventhub": None}):
            with pytest.raises((ImportError, TypeError)):
                publisher.connect()


class TestEventHubsPublisherPublish:
    def _make_message(self, payload: bytes = b"hello", headers: Optional[dict] = None) -> Message:
        return Message(
            payload=payload,
            headers=headers or {},
            topic="test-topic",
            timestamp=datetime.now(),
        )

    def test_publish_sends_event_batch(self):
        mock_event_data_cls = MagicMock()
        mock_batch = MagicMock()
        mock_client = MagicMock()
        mock_client.create_batch.return_value = mock_batch

        publisher = EventHubsPublisher(_make_config())
        publisher.client = mock_client

        with patch.dict("sys.modules", {
            "azure.eventhub": MagicMock(EventData=mock_event_data_cls),
        }):
            from azure.eventhub import EventData  # noqa: F401 – already patched
            publisher.publish(self._make_message(), "my-hub")

        mock_client.create_batch.assert_called_once()
        mock_batch.add.assert_called_once()
        mock_client.send_batch.assert_called_once_with(mock_batch)

    def test_publish_sets_properties_from_headers(self):
        mock_event = MagicMock()
        mock_event_data_cls = MagicMock(return_value=mock_event)
        mock_batch = MagicMock()
        mock_client = MagicMock()
        mock_client.create_batch.return_value = mock_batch

        publisher = EventHubsPublisher(_make_config())
        publisher.client = mock_client

        msg = self._make_message(headers={"key": "value"})
        with patch.dict("sys.modules", {
            "azure.eventhub": MagicMock(EventData=mock_event_data_cls),
        }):
            publisher.publish(msg, "hub")

        assert mock_event.properties == {"key": "value"}

    def test_publish_raises_when_not_connected(self):
        publisher = EventHubsPublisher(_make_config())
        with pytest.raises(RuntimeError, match="not connected"):
            publisher.publish(self._make_message(), "hub")

    def test_flush_is_no_op(self):
        publisher = EventHubsPublisher(_make_config())
        publisher.flush()  # should not raise

    def test_close_calls_client_close(self):
        publisher = EventHubsPublisher(_make_config())
        publisher.client = MagicMock()
        publisher.close()
        publisher.client.close.assert_called_once()

    def test_close_is_safe_when_not_connected(self):
        publisher = EventHubsPublisher(_make_config())
        publisher.close()  # should not raise
