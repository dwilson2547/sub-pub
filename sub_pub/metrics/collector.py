"""Metrics collection for monitoring message flow"""
from dataclasses import dataclass, field
from typing import Dict
from threading import Lock
import time


@dataclass
class TopicMetrics:
    """Metrics for a specific topic"""
    message_count: int = 0
    total_bytes: int = 0
    error_count: int = 0
    last_message_time: float = 0.0
    
    def record_message(self, size: int) -> None:
        """Record a successful message"""
        self.message_count += 1
        self.total_bytes += size
        self.last_message_time = time.time()
    
    def record_error(self) -> None:
        """Record an error"""
        self.error_count += 1


class MetricsCollector:
    """Thread-safe metrics collector"""
    
    def __init__(self):
        self._source_metrics: Dict[str, TopicMetrics] = {}
        self._destination_metrics: Dict[str, TopicMetrics] = {}
        self._lock = Lock()
        self._start_time = time.time()
    
    def record_source_message(self, topic: str, size: int) -> None:
        """Record a message received from a source topic"""
        with self._lock:
            if topic not in self._source_metrics:
                self._source_metrics[topic] = TopicMetrics()
            self._source_metrics[topic].record_message(size)
    
    def record_destination_message(self, topic: str, size: int) -> None:
        """Record a message sent to a destination topic"""
        with self._lock:
            if topic not in self._destination_metrics:
                self._destination_metrics[topic] = TopicMetrics()
            self._destination_metrics[topic].record_message(size)
    
    def record_source_error(self, topic: str) -> None:
        """Record an error from a source topic"""
        with self._lock:
            if topic not in self._source_metrics:
                self._source_metrics[topic] = TopicMetrics()
            self._source_metrics[topic].record_error()
    
    def record_destination_error(self, topic: str) -> None:
        """Record an error to a destination topic"""
        with self._lock:
            if topic not in self._destination_metrics:
                self._destination_metrics[topic] = TopicMetrics()
            self._destination_metrics[topic].record_error()
    
    def get_metrics(self) -> Dict:
        """Get all metrics"""
        with self._lock:
            uptime = time.time() - self._start_time
            return {
                'uptime_seconds': uptime,
                'source_metrics': {
                    topic: {
                        'message_count': metrics.message_count,
                        'total_bytes': metrics.total_bytes,
                        'error_count': metrics.error_count,
                        'last_message_time': metrics.last_message_time,
                        'rate_per_second': metrics.message_count / uptime if uptime > 0 else 0
                    }
                    for topic, metrics in self._source_metrics.items()
                },
                'destination_metrics': {
                    topic: {
                        'message_count': metrics.message_count,
                        'total_bytes': metrics.total_bytes,
                        'error_count': metrics.error_count,
                        'last_message_time': metrics.last_message_time,
                        'rate_per_second': metrics.message_count / uptime if uptime > 0 else 0
                    }
                    for topic, metrics in self._destination_metrics.items()
                }
            }
    
    def reset(self) -> None:
        """Reset all metrics"""
        with self._lock:
            self._source_metrics.clear()
            self._destination_metrics.clear()
            self._start_time = time.time()
