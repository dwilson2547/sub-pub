"""Metrics collection and reporting"""
from sub_pub.metrics.collector import MetricsCollector

try:
    from sub_pub.metrics.otel import OTelMetricsCollector
    __all__ = ["MetricsCollector", "OTelMetricsCollector"]
except ImportError:
    __all__ = ["MetricsCollector"]
