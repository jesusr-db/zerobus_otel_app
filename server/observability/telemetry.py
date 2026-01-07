"""Simple OpenTelemetry setup for FastAPI with console exporters.

This module provides a simple, all-in-one setup for OpenTelemetry instrumentation:
- Traces: Auto-instrumentation for FastAPI HTTP requests
- Metrics: HTTP request metrics and custom metrics support
- Logs: Log export with trace correlation

All telemetry is exported to console (stdout) for easy debugging.
"""

import logging
import sys
from typing import Optional, Sequence

from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor, SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


class DebugSpanExporter(SpanExporter):
    """Wrapper around ConsoleSpanExporter with debug logging."""

    def __init__(self):
        self.console_exporter = ConsoleSpanExporter(out=sys.stdout)
        print("[SPAN_EXPORTER] DebugSpanExporter initialized", flush=True)
        logger.info("SPAN_EXPORTER: Initialized")

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans with debug logging."""
        print(f"[SPAN_EXPORTER] export() called with {len(spans)} span(s)", flush=True)
        logger.info(f"SPAN_EXPORTER: export() called with {len(spans)} spans")

        for i, span in enumerate(spans):
            print(f"[SPAN_EXPORTER] Span {i+1}: name='{span.name}' trace_id={format(span.context.trace_id, '032x')}", flush=True)
            logger.info(f"SPAN_EXPORTER: Span {i+1}: {span.name}")

        # Call the actual console exporter
        result = self.console_exporter.export(spans)
        print(f"[SPAN_EXPORTER] export() completed with result: {result}", flush=True)
        return result

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        print("[SPAN_EXPORTER] shutdown() called", flush=True)
        self.console_exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush."""
        print("[SPAN_EXPORTER] force_flush() called", flush=True)
        return self.console_exporter.force_flush(timeout_millis)


def setup_telemetry_providers(service_name: str = "o11y-app-backend") -> None:
    """Set up OpenTelemetry providers and global instrumentation.

    MUST be called BEFORE creating FastAPI app for auto-instrumentation to work.

    Args:
        service_name: Name of the service for telemetry identification
    """
    print(f"[TELEMETRY] Setting up OpenTelemetry providers for service: {service_name}", flush=True)

    # Create resource with service name
    resource = Resource.create({SERVICE_NAME: service_name})

    # ============================================================================
    # TRACES: Debug span exporter with logging
    # ============================================================================
    tracer_provider = TracerProvider(resource=resource)
    debug_span_exporter = DebugSpanExporter()
    tracer_provider.add_span_processor(SimpleSpanProcessor(debug_span_exporter))
    trace.set_tracer_provider(tracer_provider)
    print("[TELEMETRY] ✅ Traces configured with DebugSpanExporter", flush=True)

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
    # SKIP GLOBAL INSTRUMENTATION: Will instrument app explicitly after creation
    # ============================================================================
    print("[TELEMETRY] Skipping global FastAPI instrumentation (will instrument app explicitly)", flush=True)

    # Create a test span to verify tracer works
    print("[TELEMETRY] Creating test span to verify tracer...", flush=True)
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-startup-span") as span:
        span.set_attribute("test", "startup")
        print(f"[TELEMETRY] Test span created: {span.name}", flush=True)
    print("[TELEMETRY] Test span should have been exported above", flush=True)

    print(f"[TELEMETRY] ✅ OpenTelemetry providers setup complete for {service_name}", flush=True)
    logger.info(f"OpenTelemetry providers initialized for {service_name}")


def instrument_app_explicitly(app) -> None:
    """Explicitly instrument FastAPI app instance (call after all routes added).

    Args:
        app: FastAPI app instance to instrument
    """
    print(f"[TELEMETRY] Explicitly instrumenting app: {app.title}", flush=True)
    print(f"[TELEMETRY] BEFORE: App has {len(app.user_middleware)} middleware", flush=True)
    print(f"[TELEMETRY] BEFORE: App has {len(app.routes)} routes", flush=True)

    try:
        # Create a fresh instrumentor instance
        instrumentor = FastAPIInstrumentor()

        # Check if already instrumented
        if hasattr(instrumentor, '_instrument_app'):
            print(f"[TELEMETRY] Instrumentor has _instrument_app: {hasattr(instrumentor, '_instrument_app')}", flush=True)

        # Instrument the specific app instance with tracer provider
        instrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())
        print("[TELEMETRY] ✅ instrument_app() called with tracer_provider", flush=True)
    except Exception as e:
        import traceback
        print(f"[TELEMETRY] ⚠️  instrument_app() failed: {e}", flush=True)
        print(f"[TELEMETRY] Traceback: {traceback.format_exc()}", flush=True)

    print(f"[TELEMETRY] AFTER: App has {len(app.user_middleware)} middleware", flush=True)

    # Check if OTEL middleware was added
    middleware_names = [str(type(m)) for m in app.user_middleware]
    print(f"[TELEMETRY] Middleware types: {middleware_names}", flush=True)

    if any("opentelemetry" in str(m).lower() or "otel" in str(m).lower() for m in app.user_middleware):
        print("[TELEMETRY] ✅ OpenTelemetry middleware detected!", flush=True)
    else:
        print("[TELEMETRY] ⚠️  OpenTelemetry middleware NOT found in app.user_middleware", flush=True)
        print("[TELEMETRY] Checking app.middleware_stack...", flush=True)
        if hasattr(app, 'middleware_stack'):
            print(f"[TELEMETRY]   middleware_stack = {app.middleware_stack}", flush=True)

        # Try to manually add middleware as last resort with proper parameters
        print("[TELEMETRY] Attempting manual middleware addition with tracer...", flush=True)
        try:
            from opentelemetry.instrumentation.fastapi import OpenTelemetryMiddleware

            # Get the tracer for the middleware
            tracer_provider = trace.get_tracer_provider()
            tracer = tracer_provider.get_tracer("opentelemetry.instrumentation.fastapi")

            # Add middleware with tracer
            app.add_middleware(
                OpenTelemetryMiddleware,
                tracer=tracer,
                tracer_provider=tracer_provider
            )
            print(f"[TELEMETRY] ✅ Manually added OpenTelemetryMiddleware with tracer", flush=True)
            print(f"[TELEMETRY] NOW: App has {len(app.user_middleware)} middleware", flush=True)

            # Rebuild middleware stack to activate the new middleware
            if hasattr(app, 'build_middleware_stack'):
                print("[TELEMETRY] Rebuilding middleware stack...", flush=True)
                app.build_middleware_stack()
                print("[TELEMETRY] ✅ Middleware stack rebuilt", flush=True)

        except Exception as manual_error:
            import traceback
            print(f"[TELEMETRY] ⚠️  Manual middleware addition failed: {manual_error}", flush=True)
            print(f"[TELEMETRY] Traceback: {traceback.format_exc()}", flush=True)


def verify_instrumentation(app) -> None:
    """Verify that FastAPI app was instrumented (call after app creation).

    Args:
        app: FastAPI app instance to verify
    """
    print(f"[TELEMETRY] Verifying instrumentation for app: {app.title}", flush=True)
    print(f"[TELEMETRY] App has {len(app.routes)} routes", flush=True)
    print(f"[TELEMETRY] App has {len(app.user_middleware)} middleware", flush=True)

    # Check if OTEL middleware was added
    middleware_names = [str(type(m)) for m in app.user_middleware]
    print(f"[TELEMETRY] Middleware types: {middleware_names}", flush=True)

    if any("opentelemetry" in str(m).lower() or "otel" in str(m).lower() for m in app.user_middleware):
        print("[TELEMETRY] ✅ OpenTelemetry middleware detected!", flush=True)
    else:
        print("[TELEMETRY] ⚠️  OpenTelemetry middleware NOT found in app.user_middleware", flush=True)
        print("[TELEMETRY] Note: FastAPI may have added it internally", flush=True)


def get_tracer(name: str):
    """Get a tracer for manual instrumentation."""
    return trace.get_tracer(name)


def get_meter(name: str):
    """Get a meter for custom metrics."""
    return metrics.get_meter(name)
