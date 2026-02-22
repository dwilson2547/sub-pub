"""Unit tests for the Google Cloud Pub/Sub adapter (using mocks)."""
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from sub_pub.adapters.google_pubsub import GooglePubSubSource, GooglePubSubPublisher
from sub_pub.core.message import Message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(extras: Optional[dict] = None) -> dict:
    base = {"project_id": "test-project", "subscription_id": "test-subscription"}
    if extras:
        base.update(extras)
    return base


def _make_received_message(data: bytes, attributes: Optional[dict] = None,
                            ack_id: str = "ack-123") -> MagicMock:
    """Simulate a google.pubsub_v1 ReceivedMessage."""
    pub_msg = MagicMock()
    pub_msg.data = data
    pub_msg.attributes = attributes or {}
    pub_msg.publish_time = datetime(2024, 1, 1, tzinfo=timezone.utc)

    received = MagicMock()
    received.message = pub_msg
    received.ack_id = ack_id
    return received


def _make_pull_response(received_messages: list) -> MagicMock:
    response = MagicMock()
    response.received_messages = received_messages
    return response


# ---------------------------------------------------------------------------
# GooglePubSubSource
# ---------------------------------------------------------------------------

class TestGooglePubSubSourceConnect:
    def test_connect_creates_subscriber_and_subscription_path(self):
        mock_subscriber = MagicMock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-subscription"
        mock_pubsub = MagicMock()
        mock_pubsub.SubscriberClient.return_value = mock_subscriber

        with patch.dict("sys.modules", {"google.cloud": MagicMock(pubsub_v1=mock_pubsub),
                                        "google.cloud.pubsub_v1": mock_pubsub}):
            source = GooglePubSubSource(_make_config())
            source.connect()

        assert source.subscriber is mock_subscriber
        assert source.subscription_path == "projects/test-project/subscriptions/test-subscription"
        assert source._pending_ack_ids == []

    def test_connect_raises_on_missing_package(self):
        source = GooglePubSubSource(_make_config())
        with patch.dict("sys.modules", {"google.cloud": None, "google.cloud.pubsub_v1": None}):
            with pytest.raises((ImportError, TypeError, AttributeError)):
                source.connect()

    def test_subscribe_is_no_op(self):
        source = GooglePubSubSource(_make_config())
        source.subscriber = MagicMock()
        source.subscription_path = "projects/p/subscriptions/s"
        source.subscribe(["topic-a"])  # should not raise


class TestGooglePubSubSourceConsume:
    def _make_source_with_subscriber(self, pull_responses: list) -> "GooglePubSubSource":
        source = GooglePubSubSource(_make_config())
        mock_subscriber = MagicMock()
        # Each call to pull() returns the next response in the list, then loops
        mock_subscriber.pull.side_effect = pull_responses + [_make_pull_response([])] * 100
        source.subscriber = mock_subscriber
        source.subscription_path = "projects/p/subscriptions/s"
        source._pending_ack_ids = []
        return source

    def test_consume_yields_message_for_each_received_message(self):
        recv1 = _make_received_message(b"msg1", ack_id="ack-1")
        recv2 = _make_received_message(b"msg2", ack_id="ack-2")
        source = self._make_source_with_subscriber([
            _make_pull_response([recv1, recv2]),
        ])

        gen = source.consume()
        m1 = next(gen)
        m2 = next(gen)

        assert m1.payload == b"msg1"
        assert m2.payload == b"msg2"

    def test_consume_stores_ack_ids(self):
        recv = _make_received_message(b"data", ack_id="ack-42")
        source = self._make_source_with_subscriber([
            _make_pull_response([recv]),
        ])

        gen = source.consume()
        next(gen)

        assert "ack-42" in source._pending_ack_ids

    def test_consume_populates_headers_from_attributes(self):
        recv = _make_received_message(b"data", attributes={"env": "prod", "version": "2"})
        source = self._make_source_with_subscriber([_make_pull_response([recv])])

        msg = next(source.consume())
        assert msg.headers == {"env": "prod", "version": "2"}

    def test_consume_uses_subscription_path_as_topic(self):
        recv = _make_received_message(b"data")
        source = self._make_source_with_subscriber([_make_pull_response([recv])])

        msg = next(source.consume())
        assert msg.topic == source.subscription_path

    def test_consume_continues_after_pull_error(self):
        recv = _make_received_message(b"ok")
        source = GooglePubSubSource(_make_config())
        mock_subscriber = MagicMock()
        # First call raises, second call succeeds
        mock_subscriber.pull.side_effect = [
            Exception("transient error"),
            _make_pull_response([recv]),
            _make_pull_response([]),
        ]
        source.subscriber = mock_subscriber
        source.subscription_path = "projects/p/subscriptions/s"
        source._pending_ack_ids = []

        msg = next(source.consume())
        assert msg.payload == b"ok"

    def test_consume_raises_when_not_connected(self):
        source = GooglePubSubSource(_make_config())
        with pytest.raises(RuntimeError, match="not connected"):
            next(source.consume())


class TestGooglePubSubSourceCommit:
    def test_commit_acknowledges_pending_ack_ids(self):
        source = GooglePubSubSource(_make_config())
        source.subscriber = MagicMock()
        source.subscription_path = "projects/p/subscriptions/s"
        source._pending_ack_ids = ["ack-1", "ack-2"]

        source.commit()

        source.subscriber.acknowledge.assert_called_once_with(
            request={
                "subscription": "projects/p/subscriptions/s",
                "ack_ids": ["ack-1", "ack-2"],
            }
        )
        assert source._pending_ack_ids == []

    def test_commit_is_no_op_when_no_pending_acks(self):
        source = GooglePubSubSource(_make_config())
        source.subscriber = MagicMock()
        source.subscription_path = "projects/p/subscriptions/s"
        source._pending_ack_ids = []

        source.commit()

        source.subscriber.acknowledge.assert_not_called()

    def test_commit_tolerates_acknowledge_errors(self):
        source = GooglePubSubSource(_make_config())
        source.subscriber = MagicMock()
        source.subscriber.acknowledge.side_effect = Exception("network error")
        source.subscription_path = "projects/p/subscriptions/s"
        source._pending_ack_ids = ["ack-1"]

        source.commit()  # should not raise

    def test_commit_is_no_op_when_subscriber_is_none(self):
        source = GooglePubSubSource(_make_config())
        source._pending_ack_ids = ["ack-1"]
        source.commit()  # should not raise


class TestGooglePubSubSourceClose:
    def test_close_calls_subscriber_close(self):
        source = GooglePubSubSource(_make_config())
        source.subscriber = MagicMock()
        source.close()
        source.subscriber.close.assert_called_once()

    def test_close_is_safe_when_not_connected(self):
        source = GooglePubSubSource(_make_config())
        source.close()  # should not raise


# ---------------------------------------------------------------------------
# GooglePubSubPublisher
# ---------------------------------------------------------------------------

class TestGooglePubSubPublisherConnect:
    def test_connect_creates_publisher_client(self):
        mock_publisher = MagicMock()
        mock_pubsub = MagicMock()
        mock_pubsub.PublisherClient.return_value = mock_publisher

        with patch.dict("sys.modules", {"google.cloud": MagicMock(pubsub_v1=mock_pubsub),
                                        "google.cloud.pubsub_v1": mock_pubsub}):
            publisher = GooglePubSubPublisher(_make_config())
            publisher.connect()

        assert publisher.publisher is mock_publisher

    def test_connect_raises_on_missing_package(self):
        publisher = GooglePubSubPublisher(_make_config())
        with patch.dict("sys.modules", {"google.cloud": None, "google.cloud.pubsub_v1": None}):
            with pytest.raises((ImportError, TypeError, AttributeError)):
                publisher.connect()


class TestGooglePubSubPublisherPublish:
    def _make_message(self, payload: bytes = b"data", headers: Optional[dict] = None) -> Message:
        return Message(
            payload=payload,
            headers=headers or {},
            topic="test-topic",
            timestamp=datetime.now(),
        )

    def test_publish_sends_message_and_waits_for_future(self):
        future = MagicMock()
        mock_pub = MagicMock()
        mock_pub.topic_path.return_value = "projects/p/topics/my-topic"
        mock_pub.publish.return_value = future

        publisher = GooglePubSubPublisher(_make_config())
        publisher.publisher = mock_pub

        publisher.publish(self._make_message(b"hello"), "my-topic")

        mock_pub.publish.assert_called_once_with(
            "projects/p/topics/my-topic",
            b"hello",
        )
        future.result.assert_called_once()

    def test_publish_passes_headers_as_attributes(self):
        future = MagicMock()
        mock_pub = MagicMock()
        mock_pub.topic_path.return_value = "projects/p/topics/t"
        mock_pub.publish.return_value = future

        publisher = GooglePubSubPublisher(_make_config())
        publisher.publisher = mock_pub

        publisher.publish(self._make_message(headers={"key": "val"}), "t")

        _, kwargs = mock_pub.publish.call_args
        assert kwargs.get("key") == "val"

    def test_publish_caches_topic_path(self):
        future = MagicMock()
        mock_pub = MagicMock()
        mock_pub.topic_path.return_value = "projects/p/topics/t"
        mock_pub.publish.return_value = future

        publisher = GooglePubSubPublisher(_make_config())
        publisher.publisher = mock_pub

        publisher.publish(self._make_message(), "t")
        publisher.publish(self._make_message(), "t")

        # topic_path should only be called once (result cached)
        assert mock_pub.topic_path.call_count == 1

    def test_publish_raises_when_not_connected(self):
        publisher = GooglePubSubPublisher(_make_config())
        with pytest.raises(RuntimeError, match="not connected"):
            publisher.publish(self._make_message(), "t")

    def test_flush_is_no_op(self):
        publisher = GooglePubSubPublisher(_make_config())
        publisher.flush()  # should not raise

    def test_close_is_safe(self):
        publisher = GooglePubSubPublisher(_make_config())
        publisher.publisher = MagicMock()
        publisher.close()  # should not raise
