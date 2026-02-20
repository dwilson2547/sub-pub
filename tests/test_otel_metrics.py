"""Unit tests for the OpenTelemetry metrics module"""
import pytest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from sub_pub.metrics.otel import OTelMetricsCollector


def _make_collector() -> tuple[OTelMetricsCollector, InMemoryMetricReader]:
    """Create a collector backed by an in-memory reader for assertions."""
    reader = InMemoryMetricReader()
    # Build collector manually so we can inject a test provider
    provider = MeterProvider(metric_readers=[reader])
    collector = OTelMetricsCollector.__new__(OTelMetricsCollector)
    collector._provider = provider
    meter = provider.get_meter("sub_pub")
    collector._source_messages = meter.create_counter(
        name="sub_pub.source.messages", description="test", unit="1"
    )
    collector._source_bytes = meter.create_counter(
        name="sub_pub.source.bytes", description="test", unit="By"
    )
    collector._source_errors = meter.create_counter(
        name="sub_pub.source.errors", description="test", unit="1"
    )
    collector._destination_messages = meter.create_counter(
        name="sub_pub.destination.messages", description="test", unit="1"
    )
    collector._destination_bytes = meter.create_counter(
        name="sub_pub.destination.bytes", description="test", unit="By"
    )
    collector._destination_errors = meter.create_counter(
        name="sub_pub.destination.errors", description="test", unit="1"
    )
    return collector, reader


def _collect(reader: InMemoryMetricReader) -> dict:
    """Return a flat dict mapping metric-name -> {attribute-set -> value}."""
    data = reader.get_metrics_data()
    result: dict = {}
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                result[metric.name] = {}
                for dp in metric.data.data_points:
                    key = frozenset(dp.attributes.items()) if dp.attributes else frozenset()
                    result[metric.name][key] = dp.value
    return result


class TestOTelMetricsCollector:
    def test_record_source_message(self):
        collector, reader = _make_collector()
        collector.record_source_message("topic-a", 256)
        collector.record_source_message("topic-a", 128)

        data = _collect(reader)
        topic_a = frozenset({"topic": "topic-a"}.items())
        assert data["sub_pub.source.messages"][topic_a] == 2
        assert data["sub_pub.source.bytes"][topic_a] == 384

    def test_record_destination_message(self):
        collector, reader = _make_collector()
        collector.record_destination_message("dest-topic", 512)

        data = _collect(reader)
        key = frozenset({"topic": "dest-topic"}.items())
        assert data["sub_pub.destination.messages"][key] == 1
        assert data["sub_pub.destination.bytes"][key] == 512

    def test_record_source_error(self):
        collector, reader = _make_collector()
        collector.record_source_error("topic-err")
        collector.record_source_error("topic-err")

        data = _collect(reader)
        key = frozenset({"topic": "topic-err"}.items())
        assert data["sub_pub.source.errors"][key] == 2

    def test_record_destination_error(self):
        collector, reader = _make_collector()
        collector.record_destination_error("dest-err")

        data = _collect(reader)
        key = frozenset({"topic": "dest-err"}.items())
        assert data["sub_pub.destination.errors"][key] == 1

    def test_multiple_topics_tracked_separately(self):
        collector, reader = _make_collector()
        collector.record_source_message("topic-x", 100)
        collector.record_source_message("topic-y", 200)

        data = _collect(reader)
        key_x = frozenset({"topic": "topic-x"}.items())
        key_y = frozenset({"topic": "topic-y"}.items())
        assert data["sub_pub.source.messages"][key_x] == 1
        assert data["sub_pub.source.messages"][key_y] == 1
        assert data["sub_pub.source.bytes"][key_x] == 100
        assert data["sub_pub.source.bytes"][key_y] == 200

    def test_shutdown_does_not_raise(self):
        collector, _ = _make_collector()
        collector.shutdown()  # should not raise

    def test_import_error_raises_informative_message(self):
        """OTelMetricsCollector raises ImportError when opentelemetry is absent."""
        import sub_pub.metrics.otel as otel_module
        original = otel_module._OTEL_AVAILABLE
        try:
            otel_module._OTEL_AVAILABLE = False
            with pytest.raises(ImportError, match="pip install sub-pub\\[opentelemetry\\]"):
                OTelMetricsCollector()
        finally:
            otel_module._OTEL_AVAILABLE = original

    def test_exporter_argument_accepted(self):
        """OTelMetricsCollector accepts an exporter and builds a PeriodicExportingMetricReader."""
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
        exporter = ConsoleMetricExporter()
        # Should not raise
        collector = OTelMetricsCollector(exporter=exporter, export_interval_millis=60_000)
        collector.shutdown()
