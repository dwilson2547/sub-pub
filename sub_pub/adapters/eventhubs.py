"""Azure Event Hubs adapter"""
import logging
import queue
import threading
from typing import Iterator, List, Optional

from sub_pub.core.interfaces import MessageSource, MessagePublisher
from sub_pub.core.message import Message

logger = logging.getLogger(__name__)


class EventHubsSource(MessageSource):
    """Azure Event Hubs message source"""

    def __init__(self, config: dict):
        self.config = config
        self.client = None
        self._event_queue: Optional[queue.Queue] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._last_event_per_partition: dict = {}

    def connect(self) -> None:
        """Establish connection to Event Hubs"""
        try:
            from azure.eventhub import EventHubConsumerClient

            self.client = EventHubConsumerClient.from_connection_string(
                self.config['connection_string'],
                consumer_group=self.config.get('consumer_group', '$Default'),
                **{k: v for k, v in self.config.items()
                   if k not in ['connection_string', 'consumer_group']}
            )
            logger.info("Connected to Event Hubs source")
        except ImportError:
            logger.error("azure-eventhub package not installed. Install with: pip install azure-eventhub")
            raise

    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics (Event Hubs uses partitions, not named topics)"""
        logger.info("Event Hubs subscribed (topics parameter not used; consuming all partitions)")

    def consume(self) -> Iterator[Message]:
        """Consume messages from Event Hubs using a background receive thread.

        Optional config keys:
          - ``queue_size`` (int, default 1000): internal buffer between the
            receive callback and this iterator.
          - ``starting_position`` (str, default ``"-1"``): partition offset to
            start reading from (``"-1"`` = latest, ``"@latest"`` also accepted).
        """
        if not self.client:
            raise RuntimeError("Client not connected")

        self._event_queue = queue.Queue(maxsize=self.config.get('queue_size', 1000))
        self._last_event_per_partition = {}

        def _on_event(partition_context, event):
            if event is None:
                return
            raw_props = event.properties or {}
            headers = {
                k.decode('utf-8') if isinstance(k, bytes) else str(k):
                v.decode('utf-8') if isinstance(v, bytes) else str(v)
                for k, v in raw_props.items()
            }
            msg = Message(
                payload=event.body_as_bytes(),
                headers=headers,
                topic=f"eventhub-{partition_context.partition_id}",
                partition=int(partition_context.partition_id),
                offset=event.offset,
                timestamp=event.enqueued_time,
            )
            # Track latest event per partition for checkpointing
            self._last_event_per_partition[partition_context.partition_id] = (
                partition_context,
                event,
            )
            self._event_queue.put(msg, block=True)

        def _on_error(partition_context, error):
            pid = partition_context.partition_id if partition_context else "N/A"
            logger.error(f"Event Hubs error on partition {pid}: {error}")

        starting_position = self.config.get('starting_position', '-1')
        self._receive_thread = threading.Thread(
            target=self.client.receive,
            kwargs={
                'on_event': _on_event,
                'on_error': _on_error,
                'starting_position': starting_position,
            },
            daemon=True,
        )
        self._receive_thread.start()

        # Drain remaining items after the receive thread has exited.
        # The thread is the sole producer, so once is_alive() is False no new
        # items can be enqueued; we simply flush whatever is left in the buffer.
        while self._receive_thread.is_alive() or not self._event_queue.empty():
            try:
                msg = self._event_queue.get(timeout=1.0)
                yield msg
            except queue.Empty:
                continue

    def close(self) -> None:
        """Close Event Hubs connection"""
        if self.client:
            self.client.close()
            logger.info("Event Hubs source closed")

    def commit(self, message: Optional[Message] = None) -> None:
        """Update checkpoints for all partitions that have received events."""
        for partition_id, (partition_context, event) in list(self._last_event_per_partition.items()):
            try:
                partition_context.update_checkpoint(event)
            except Exception as e:
                logger.error(f"Error updating checkpoint for partition {partition_id}: {e}")
        self._last_event_per_partition = {}


class EventHubsPublisher(MessagePublisher):
    """Azure Event Hubs message publisher"""

    def __init__(self, config: dict):
        self.config = config
        self.client = None

    def connect(self) -> None:
        """Establish connection to Event Hubs"""
        try:
            from azure.eventhub import EventHubProducerClient

            self.client = EventHubProducerClient.from_connection_string(
                self.config['connection_string'],
                **{k: v for k, v in self.config.items() if k != 'connection_string'}
            )
            logger.info("Connected to Event Hubs publisher")
        except ImportError:
            logger.error("azure-eventhub package not installed. Install with: pip install azure-eventhub")
            raise

    def publish(self, message: Message, topic: str) -> None:
        """Publish a message to Event Hubs as a single-event batch."""
        if not self.client:
            raise RuntimeError("Client not connected")

        from azure.eventhub import EventData

        event = EventData(message.payload)
        if message.headers:
            event.properties = {k: v for k, v in message.headers.items()}

        event_batch = self.client.create_batch()
        event_batch.add(event)
        self.client.send_batch(event_batch)

    def flush(self) -> None:
        """Flush buffered messages (no-op; each publish sends immediately)."""
        pass

    def close(self) -> None:
        """Close Event Hubs connection"""
        if self.client:
            self.client.close()
            logger.info("Event Hubs publisher closed")
