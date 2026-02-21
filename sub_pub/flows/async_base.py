"""Async base flow using asyncio for non-blocking I/O"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from sub_pub.core.message import Message
from sub_pub.core.interfaces import AsyncMessageSource, AsyncMessagePublisher
from sub_pub.domain.processor import AsyncMessageProcessor, AsyncPassThroughProcessor
from sub_pub.metrics.collector import MetricsCollector
from sub_pub.config.models import ThreadPoolConfig, BackPressureConfig

logger = logging.getLogger(__name__)


class AsyncFlow(ABC):
    """Abstract base class for async message flows using asyncio"""

    def __init__(
        self,
        thread_pool_config: ThreadPoolConfig,
        back_pressure_config: BackPressureConfig,
        processor: Optional[AsyncMessageProcessor] = None,
    ):
        self.thread_pool_config = thread_pool_config
        self.back_pressure_config = back_pressure_config
        self.processor = processor or AsyncPassThroughProcessor()
        self.metrics = MetricsCollector()

        self._running = False
        self._shutdown_event: asyncio.Event
        self._domain_queue: asyncio.Queue
        self._publish_queue: asyncio.Queue

    def _init_queues(self) -> None:
        """Initialise asyncio queues (must be called inside a running event loop)."""
        self._shutdown_event = asyncio.Event()
        self._domain_queue = asyncio.Queue(
            maxsize=self.thread_pool_config.queue_size
        )
        self._publish_queue = asyncio.Queue(
            maxsize=self.thread_pool_config.queue_size
        )

    async def _check_back_pressure(self, queue: asyncio.Queue) -> bool:
        """Check if back-pressure should be applied"""
        if not self.back_pressure_config.enabled or queue.maxsize <= 0:
            return False
        queue_usage = queue.qsize() / queue.maxsize
        return queue_usage >= self.back_pressure_config.queue_high_watermark

    async def _wait_for_back_pressure_release(self, queue: asyncio.Queue) -> None:
        """Wait until the queue drains below the low-watermark"""
        while self._running:
            queue_usage = queue.qsize() / queue.maxsize if queue.maxsize > 0 else 0
            if queue_usage <= self.back_pressure_config.queue_low_watermark:
                break
            await asyncio.sleep(0.01)

    async def _domain_worker(self) -> None:
        """Coroutine for domain processing"""
        while self._running:
            try:
                message, dest_topic = await asyncio.wait_for(
                    self._domain_queue.get(), timeout=0.1
                )
            except asyncio.TimeoutError:
                continue

            try:
                processed_message = await self.processor.process(message)

                if await self._check_back_pressure(self._publish_queue):
                    logger.debug("Back-pressure detected on publish queue, waiting...")
                    await self._wait_for_back_pressure_release(self._publish_queue)

                await self._publish_queue.put((processed_message, dest_topic))
            except Exception as e:
                logger.error(f"Error in domain processing: {e}", exc_info=True)
                self.metrics.record_source_error(message.topic)
            finally:
                self._domain_queue.task_done()

    async def _publish_worker(self, publisher: AsyncMessagePublisher) -> None:
        """Coroutine for publishing messages"""
        while self._running:
            try:
                message, dest_topic = await asyncio.wait_for(
                    self._publish_queue.get(), timeout=0.1
                )
            except asyncio.TimeoutError:
                continue

            try:
                await publisher.publish(message, dest_topic)
                self.metrics.record_destination_message(dest_topic, message.size())
            except Exception as e:
                logger.error(f"Error publishing message: {e}", exc_info=True)
                self.metrics.record_destination_error(dest_topic)
            finally:
                self._publish_queue.task_done()

    @abstractmethod
    async def run(self) -> None:
        """Run the flow"""
        pass

    async def shutdown(self) -> None:
        """Shutdown the flow"""
        logger.info("Shutting down async flow...")
        self._running = False
        self._shutdown_event.set()

        # Wait for queues to drain
        await self._domain_queue.join()
        await self._publish_queue.join()

        logger.info("Async flow shutdown complete")
