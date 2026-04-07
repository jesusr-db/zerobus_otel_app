import os

# Lakebase configuration (PostgreSQL backend)
# Connection is auto-discovered via app resource binding (PG* env vars)
# or falls back to manual env vars for local development
LAKEBASE_INSTANCE_NAME = os.getenv("LAKEBASE_INSTANCE_NAME", "zerobus-dev")
LAKEBASE_DATABASE_NAME = os.getenv("PGDATABASE", os.getenv("LAKEBASE_DATABASE_NAME", "zerobus_sdp"))
LAKEBASE_CATALOG_NAME = os.getenv("LAKEBASE_CATALOG_NAME", "zerobus_sdp")
LAKEBASE_SCHEMA_NAME = os.getenv("LAKEBASE_SCHEMA_NAME", "zerobus_sdp")
LAKEBASE_HOST = os.getenv("PGHOST", os.getenv("LAKEBASE_HOST", ""))
LAKEBASE_PORT = int(os.getenv("PGPORT", os.getenv("LAKEBASE_PORT", "5432")))
