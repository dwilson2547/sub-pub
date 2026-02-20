"""OpenTelemetry metrics integration for sub-pub"""
from typing import Optional

try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        MetricExporter,
        PeriodicExportingMetricReader,
    )
    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OTEL_AVAILABLE = False


class OTelMetricsCollector:
    """
    Metrics collector that publishes sub-pub metrics via OpenTelemetry.

    Usage::

        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
        collector = OTelMetricsCollector(exporter=ConsoleMetricExporter())
        collector.record_source_message("my-topic", 128)

    The collector is a drop-in companion to :class:`~sub_pub.metrics.collector.MetricsCollector`;
    both share the same recording interface so they can be used side-by-side or as replacements.
    """

    def __init__(
        self,
        exporter: Optional["MetricExporter"] = None,
        export_interval_millis: int = 30_000,
        meter_name: str = "sub_pub",
    ):
        if not _OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry packages are required for OTelMetricsCollector. "
                "Install them with: pip install sub-pub[opentelemetry]"
            )

        if exporter is not None:
            reader = PeriodicExportingMetricReader(
                exporter, export_interval_millis=export_interval_millis
            )
            self._provider = MeterProvider(metric_readers=[reader])
        else:
            self._provider = MeterProvider()

        meter = self._provider.get_meter(meter_name)

        self._source_messages = meter.create_counter(
            name="sub_pub.source.messages",
            description="Number of messages received from source topics",
            unit="1",
        )
        self._source_bytes = meter.create_counter(
            name="sub_pub.source.bytes",
            description="Total bytes received from source topics",
            unit="By",
        )
        self._source_errors = meter.create_counter(
            name="sub_pub.source.errors",
            description="Number of errors from source topics",
            unit="1",
        )
        self._destination_messages = meter.create_counter(
            name="sub_pub.destination.messages",
            description="Number of messages sent to destination topics",
            unit="1",
        )
        self._destination_bytes = meter.create_counter(
            name="sub_pub.destination.bytes",
            description="Total bytes sent to destination topics",
            unit="By",
        )
        self._destination_errors = meter.create_counter(
            name="sub_pub.destination.errors",
            description="Number of errors to destination topics",
            unit="1",
        )

    def record_source_message(self, topic: str, size: int) -> None:
        """Record a message received from a source topic"""
        attrs = {"topic": topic}
        self._source_messages.add(1, attrs)
        self._source_bytes.add(size, attrs)

    def record_destination_message(self, topic: str, size: int) -> None:
        """Record a message sent to a destination topic"""
        attrs = {"topic": topic}
        self._destination_messages.add(1, attrs)
        self._destination_bytes.add(size, attrs)

    def record_source_error(self, topic: str) -> None:
        """Record an error from a source topic"""
        self._source_errors.add(1, {"topic": topic})

    def record_destination_error(self, topic: str) -> None:
        """Record an error to a destination topic"""
        self._destination_errors.add(1, {"topic": topic})

    def shutdown(self) -> None:
        """Flush pending metrics and shut down the meter provider"""
        self._provider.shutdown()
