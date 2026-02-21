"""Async one-to-one flow: multiple source-destination pairs"""
import asyncio
import logging
from typing import Dict, List, Optional

from sub_pub.flows.async_base import AsyncFlow
from sub_pub.core.interfaces import AsyncMessageSource, AsyncMessagePublisher
from sub_pub.config.models import OneToOneMapping

logger = logging.getLogger(__name__)


class AsyncOneToOneFlow(AsyncFlow):
    """Async one-to-one flow: multiple independent source->destination mappings"""

    def __init__(
        self,
        source: AsyncMessageSource,
        destination: AsyncMessagePublisher,
        mappings: List[OneToOneMapping],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.source = source
        self.destination = destination
        self.mappings = mappings

        self.topic_map: Dict[str, str] = {
            m.source_topic: m.destination_topic for m in mappings
        }

    async def _consume_messages(self) -> None:
        """Consume messages from source"""
        try:
            async for message in self.source.consume():
                if not self._running:
                    break

                try:
                    dest_topic = self.topic_map.get(message.topic)
                    if dest_topic is None:
                        logger.debug(
                            f"No mapping found for topic {message.topic}, skipping"
                        )
                        continue

                    self.metrics.record_source_message(message.topic, message.size())

                    if await self._check_back_pressure(self._domain_queue):
                        logger.debug(
                            "Back-pressure detected on domain queue, waiting..."
                        )
                        await self._wait_for_back_pressure_release(self._domain_queue)

                    await self._domain_queue.put((message, dest_topic))
                    await self.source.commit(message)

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    self.metrics.record_source_error(message.topic)
        except Exception as e:
            logger.error(f"Error consuming messages: {e}", exc_info=True)

    async def run(self) -> None:
        """Run the async one-to-one flow"""
        self._init_queues()
        self._running = True

        await self.source.connect()
        source_topics = [m.source_topic for m in self.mappings]
        await self.source.subscribe(source_topics)
        await self.destination.connect()

        workers = (
            [self._consume_messages()]
            + [self._domain_worker() for _ in range(self.thread_pool_config.max_workers)]
            + [
                self._publish_worker(self.destination)
                for _ in range(self.thread_pool_config.max_workers)
            ]
        )

        logger.info(
            f"Async one-to-one flow started with {len(self.mappings)} mappings"
        )

        tasks = [asyncio.create_task(w) for w in workers]

        await self._shutdown_event.wait()

        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        await self.destination.flush()
        await self.destination.close()
        await self.source.close()

        logger.info("Async one-to-one flow stopped")
