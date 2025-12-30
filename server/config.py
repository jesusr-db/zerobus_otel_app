import os

# Observability table configuration
OBSERVABILITY_CATALOG = os.getenv("CATALOG_NAME", "jmr_demo")
OBSERVABILITY_SCHEMA = os.getenv("SCHEMA_NAME", "zerobus_sdp")
OBSERVABILITY_TABLE_PREFIX = f"{OBSERVABILITY_CATALOG}.{OBSERVABILITY_SCHEMA}"

# Lakebase configuration
LAKEBASE_INSTANCE_NAME = os.getenv("LAKEBASE_INSTANCE_NAME", "zerobus-dev")
LAKEBASE_DATABASE_NAME = os.getenv("LAKEBASE_DATABASE_NAME", "databricks_postgres")
LAKEBASE_CATALOG_NAME = os.getenv("LAKEBASE_CATALOG_NAME", "zerobus_sdp")
LAKEBASE_SCHEMA_NAME = os.getenv("LAKEBASE_SCHEMA_NAME", "zerobus_sdp")
LAKEBASE_HOST = os.getenv("LAKEBASE_HOST", "")  # Set via environment
LAKEBASE_PORT = int(os.getenv("LAKEBASE_PORT", "5432"))

# Data backend selection: "warehouse" or "lakebase"
DATA_BACKEND = os.getenv("DATA_BACKEND", "lakebase")
