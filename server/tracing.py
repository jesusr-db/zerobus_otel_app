"""OpenTelemetry tracing configuration for Databricks App."""

import os
import logging

# Enable OpenTelemetry debug logging
logging.getLogger('opentelemetry').setLevel(logging.DEBUG)
logging.getLogger('opentelemetry.sdk.trace').setLevel(logging.DEBUG)
logging.getLogger('opentelemetry.exporter').setLevel(logging.DEBUG)
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry._logs import set_logger_provider


def setup_tracing():
  """Configure OpenTelemetry instrumentation for traces, metrics, and logs."""
  resource = Resource(attributes={'service.name': 'o11y-app'})

  databricks_host = os.getenv('DATABRICKS_HOST')
  otel_token = os.getenv('OTEL_TOKEN')
  otel_traces_table = os.getenv('OTEL_TRACES_TABLE')
  otel_metrics_table = os.getenv('OTEL_METRICS_TABLE')
  otel_logs_table = os.getenv('OTEL_LOGS_TABLE')

  if not all(
    [databricks_host, otel_token, otel_traces_table, otel_metrics_table, otel_logs_table]
  ):
    raise ValueError(
      'Missing required environment variables: DATABRICKS_HOST, OTEL_TOKEN, '
      'OTEL_TRACES_TABLE, OTEL_METRICS_TABLE, OTEL_LOGS_TABLE'
    )

  otlp_trace_exporter = OTLPSpanExporter(
    endpoint=f'{databricks_host}/api/2.0/otel/v1/traces',
    headers={
      'content-type': 'application/x-protobuf',
      'X-Databricks-UC-Table-Name': otel_traces_table,
      'Authorization': f'Bearer {otel_token}',
    },
  )

  otlp_metric_exporter = OTLPMetricExporter(
    endpoint=f'{databricks_host}/api/2.0/otel/v1/metrics',
    headers={
      'content-type': 'application/x-protobuf',
      'X-Databricks-UC-Table-Name': otel_metrics_table,
      'Authorization': f'Bearer {otel_token}',
    },
  )

  otlp_log_exporter = OTLPLogExporter(
    endpoint=f'{databricks_host}/api/2.0/otel/v1/logs',
    headers={
      'content-type': 'application/x-protobuf',
      'X-Databricks-UC-Table-Name': otel_logs_table,
      'Authorization': f'Bearer {otel_token}',
    },
  )

  trace_provider = TracerProvider(resource=resource)
  # Use shorter batch intervals for faster export (default is 5000ms)
  span_processor = BatchSpanProcessor(
    otlp_trace_exporter,
    max_queue_size=2048,
    schedule_delay_millis=1000,  # Export every 1 second
    max_export_batch_size=512,
  )
  trace_provider.add_span_processor(span_processor)
  trace.set_tracer_provider(trace_provider)
  
  logger = logging.getLogger(__name__)
  logger.info(f'TracerProvider set with BatchSpanProcessor (export every 1s)')
  logger.info(f'Current tracer provider: {trace.get_tracer_provider()}')

  metric_reader = PeriodicExportingMetricReader(
    otlp_metric_exporter, export_interval_millis=10000
  )
  meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
  metrics.set_meter_provider(meter_provider)

  logger_provider = LoggerProvider(resource=resource)
  logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
  set_logger_provider(logger_provider)

  handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
  logging.getLogger().addHandler(handler)

  LoggingInstrumentor().instrument(set_logging_format=True)

  SystemMetricsInstrumentor().instrument()

  logger.info('=' * 80)
  logger.info(f'✅ OpenTelemetry Backend initialized (OTLP to {databricks_host})')
  logger.info(f'   Service: {resource.attributes.get("service.name")}')
  logger.info(f'   Traces endpoint: {databricks_host}/api/2.0/otel/v1/traces')
  logger.info(f'   Traces → {otel_traces_table}')
  logger.info(f'   Metrics → {otel_metrics_table}')
  logger.info(f'   Logs → {otel_logs_table}')
  logger.info('=' * 80)
  
  # Test span to verify exporter is working
  tracer = trace.get_tracer(__name__)
  with tracer.start_as_current_span('otel_initialization_test'):
    logger.info('Test span created - should be exported to OTLP')
  
  # Force flush to ensure test span is sent immediately
  trace_provider.force_flush(timeout_millis=5000)
  logger.info('Forced flush of trace provider completed')
  
  return trace_provider, meter_provider
