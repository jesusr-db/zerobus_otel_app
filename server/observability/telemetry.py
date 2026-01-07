"""Simple OpenTelemetry setup for FastAPI with console exporters.

This module provides a simple, all-in-one setup for OpenTelemetry instrumentation:
- Traces: Auto-instrumentation for FastAPI HTTP requests
- Metrics: HTTP request metrics and custom metrics support
- Logs: Log export with trace correlation

All telemetry is exported to console (stdout) for easy debugging.
"""

import logging
import sys
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

logger = logging.getLogger(__name__)


def setup_telemetry(service_name: str = "o11y-app-backend", app=None) -> None:
    """Set up OpenTelemetry with console exporters for traces, metrics, and logs.

    Args:
        service_name: Name of the service for telemetry identification
        app: FastAPI app instance to instrument (optional)
    """
    print(f"[TELEMETRY] Setting up OpenTelemetry for service: {service_name}", flush=True)

    # Create resource with service name
    resource = Resource.create({SERVICE_NAME: service_name})

    # ============================================================================
    # TRACES: Console exporter with auto-instrumentation
    # ============================================================================
    tracer_provider = TracerProvider(resource=resource)
    console_span_exporter = ConsoleSpanExporter(out=sys.stdout)
    tracer_provider.add_span_processor(SimpleSpanProcessor(console_span_exporter))
    trace.set_tracer_provider(tracer_provider)
    print("[TELEMETRY] ✅ Traces configured with ConsoleSpanExporter", flush=True)

    # ============================================================================
    # METRICS: Console exporter with periodic export
    # ============================================================================
    console_metric_reader = PeriodicExportingMetricReader(
        ConsoleMetricExporter(out=sys.stdout),
        export_interval_millis=60000  # Export every 60 seconds
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[console_metric_reader])
    metrics.set_meter_provider(meter_provider)
    print("[TELEMETRY] ✅ Metrics configured with ConsoleMetricExporter (60s interval)", flush=True)

    # ============================================================================
    # LOGS: Console exporter with trace correlation
    # ============================================================================
    logger_provider = LoggerProvider(resource=resource)
    console_log_exporter = ConsoleLogExporter(out=sys.stdout)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(console_log_exporter))
    set_logger_provider(logger_provider)

    # Add OTEL logging handler to root logger
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    print("[TELEMETRY] ✅ Logs configured with ConsoleLogExporter", flush=True)

    # ============================================================================
    # AUTO-INSTRUMENTATION: FastAPI
    # ============================================================================
    if app:
        FastAPIInstrumentor.instrument_app(app)
        print(f"[TELEMETRY] ✅ FastAPI app auto-instrumented: {app.title}", flush=True)
    else:
        print("[TELEMETRY] ⚠️  No app provided, skipping FastAPI instrumentation", flush=True)

    print(f"[TELEMETRY] ✅ OpenTelemetry setup complete for {service_name}", flush=True)
    logger.info(f"OpenTelemetry telemetry initialized for {service_name}")


def get_tracer(name: str):
    """Get a tracer for manual instrumentation."""
    return trace.get_tracer(name)


def get_meter(name: str):
    """Get a meter for custom metrics."""
    return metrics.get_meter(name)
