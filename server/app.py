"""FastAPI application for Databricks App Template."""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

from server.routers import router
from server.tracing import setup_tracing

# Load environment variables from .env.local if it exists
def load_env_file(filepath: str) -> None:
  """Load environment variables from a file."""
  if Path(filepath).exists():
    with open(filepath) as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith('#'):
          key, _, value = line.partition('=')
          if key and value:
            os.environ[key] = value


# Load .env files BEFORE setting up tracing
load_env_file('.env')
load_env_file('.env.local')

logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s [%(levelname)s] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s',
)
logger = logging.getLogger(__name__)

# Setup tracing AFTER loading env vars
try:
  setup_tracing()
  logger.info('OpenTelemetry tracing initialized successfully')
except Exception as e:
  logger.warning(f'Failed to initialize OpenTelemetry: {e}')
  logger.warning('Continuing without OpenTelemetry instrumentation')


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Manage application lifespan."""
  yield


app = FastAPI(
  title='Databricks App API',
  description='Modern FastAPI application template for Databricks Apps with React frontend',
  version='0.1.0',
  lifespan=lifespan,
)

# Instrument FastAPI app with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)
logger.info('FastAPI instrumented with OpenTelemetry')


# Add custom middleware to verify span creation
@app.middleware('http')
async def trace_middleware(request: Request, call_next):
  tracer = trace.get_tracer(__name__)
  with tracer.start_as_current_span(f'{request.method} {request.url.path}') as span:
    span.set_attribute('http.method', request.method)
    span.set_attribute('http.url', str(request.url))
    logger.debug(f'Created span for {request.method} {request.url.path}')
    response = await call_next(request)
    span.set_attribute('http.status_code', response.status_code)
    return response


app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    '*'
  ],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

app.include_router(router, prefix='/api', tags=['api'])


@app.get('/health')
async def health():
  """Health check endpoint."""
  logger.info('Health check endpoint called')
  return {'status': 'healthy'}


# ============================================================================
# SERVE STATIC FILES FROM CLIENT BUILD DIRECTORY (MUST BE LAST!)
# ============================================================================
# This static file mount MUST be the last route registered!
# It catches all unmatched requests and serves the React app.
# Any routes added after this will be unreachable!
if os.path.exists('client/build'):
  app.mount('/', StaticFiles(directory='client/build', html=True), name='static')
