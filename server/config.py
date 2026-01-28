import os

# Lakebase configuration (PostgreSQL backend)
LAKEBASE_INSTANCE_NAME = os.getenv("LAKEBASE_INSTANCE_NAME", "zerobus-dev")
LAKEBASE_DATABASE_NAME = os.getenv("LAKEBASE_DATABASE_NAME", "databricks_postgres")
LAKEBASE_CATALOG_NAME = os.getenv("LAKEBASE_CATALOG_NAME", "zerobus_sdp")
LAKEBASE_SCHEMA_NAME = os.getenv("LAKEBASE_SCHEMA_NAME", "zerobus_sdp")
LAKEBASE_HOST = os.getenv("LAKEBASE_HOST", "")  # Set via environment
LAKEBASE_PORT = int(os.getenv("LAKEBASE_PORT", "5432"))
