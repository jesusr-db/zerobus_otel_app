"""OpenTelemetry setup for FastAPI with OTLP exporters to Databricks.

This module provides OpenTelemetry instrumentation with Databricks OTLP endpoints:
- Traces: Auto-instrumentation for FastAPI HTTP requests → Databricks traces table
- Metrics: HTTP request metrics and custom metrics → Databricks metrics table
- Logs: Log export with trace correlation → Databricks logs table
"""

import logging
import os
from opentelemetry import trace, metrics
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

logger = logging.getLogger(__name__)


def setup_telemetry_providers(service_name: str = "o11y-app-backend") -> None:
    """Set up OpenTelemetry providers with OTLP exporters to Databricks.

    MUST be called BEFORE creating FastAPI app for auto-instrumentation to work.

    Args:
        service_name: Name of the service for telemetry identification
    """
    # Get configuration from environment variables
    databricks_host = os.getenv("DATABRICKS_HOST", "https://myworkspace.databricks.com")
    api_token = os.getenv("DATABRICKS_OTEL_TOKEN")
    catalog_name = os.getenv("OTEL_CATALOG", "catalog")
    schema_name = os.getenv("OTEL_SCHEMA", "schema")
    table_prefix = os.getenv("OTEL_TABLE_PREFIX", "otel")
    environment = os.getenv("ENVIRONMENT", "development")

    print(f"[OTEL] Initializing OpenTelemetry for service: {service_name}", flush=True)
    print(f"[OTEL] Databricks Host: {databricks_host}", flush=True)
    print(f"[OTEL] UC Location: {catalog_name}.{schema_name}.{table_prefix}_*", flush=True)
    print(f"[OTEL] Environment: {environment}", flush=True)

    if not api_token:
        print("[OTEL] ⚠️  WARNING: DATABRICKS_TOKEN not set, telemetry export will fail", flush=True)

    # Create resource with service metadata
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": environment
    })

    # ============================================================================
    # TRACES: OTLP exporter to Databricks
    # ============================================================================
    tracer_provider = TracerProvider(
        resource=resource,
        id_generator=RandomIdGenerator()
    )

    try:
        otlp_span_exporter = OTLPSpanExporter(
            endpoint=f"{databricks_host}/api/2.0/otel/v1/traces",
            headers={
                "X-Databricks-UC-Table-Name": f"{catalog_name}.{schema_name}.{table_prefix}_traces",
                "Authorization": f"Bearer {api_token}"
            },
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
        print(f"[OTEL] ✅ OTLP span exporter configured for Databricks", flush=True)
    except Exception as e:
        print(f"[OTEL] ⚠️  Failed to configure OTLP span exporter: {e}", flush=True)

    trace.set_tracer_provider(tracer_provider)
    print(f"[OTEL] ✅ Trace provider configured", flush=True)

    # ============================================================================
    # METRICS: OTLP exporter to Databricks
    # ============================================================================
    try:
        otlp_metric_exporter = OTLPMetricExporter(
            endpoint=f"{databricks_host}/api/2.0/otel/v1/metrics",
            headers={
                "content-type": "application/x-protobuf",
                "X-Databricks-UC-Table-Name": f"{catalog_name}.{schema_name}.{table_prefix}_metrics",
                "Authorization": f"Bearer {api_token}"
            },
        )

        metric_reader = PeriodicExportingMetricReader(
            otlp_metric_exporter,
            export_interval_millis=60000  # Export every 60 seconds
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        print(f"[OTEL] ✅ Metrics configured with OTLP exporter", flush=True)
    except Exception as e:
        print(f"[OTEL] ⚠️  Failed to configure metrics exporter: {e}", flush=True)
        meter_provider = MeterProvider(resource=resource)
        metrics.set_meter_provider(meter_provider)

    # ============================================================================
    # LOGS: OTLP exporter to Databricks
    # ============================================================================
    try:
        otlp_log_exporter = OTLPLogExporter(
            endpoint=f"{databricks_host}/api/2.0/otel/v1/logs",
            headers={
                "content-type": "application/x-protobuf",
                "X-Databricks-UC-Table-Name": f"{catalog_name}.{schema_name}.{table_prefix}_logs",
                "Authorization": f"Bearer {api_token}"
            },
        )

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
        set_logger_provider(logger_provider)

        # Add OTEL logging handler to root logger
        handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        print(f"[OTEL] ✅ Logs configured with OTLP exporter", flush=True)
    except Exception as e:
        print(f"[OTEL] ⚠️  Failed to configure logs exporter: {e}", flush=True)

    print(f"[OTEL] ✅ OpenTelemetry setup complete", flush=True)
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
