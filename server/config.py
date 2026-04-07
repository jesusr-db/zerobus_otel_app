import os

# Lakebase configuration (PostgreSQL backend)
# Host is auto-discovered from instance name via SDK if not set in env.
# LakebaseManager handles the full resolution chain.
LAKEBASE_INSTANCE_NAME = os.getenv("LAKEBASE_INSTANCE_NAME", "zerobus-dev")
LAKEBASE_DATABASE_NAME = os.getenv("LAKEBASE_DATABASE_NAME", "zerobus_sdp")
LAKEBASE_CATALOG_NAME = os.getenv("LAKEBASE_CATALOG_NAME", "zerobus_sdp")
LAKEBASE_SCHEMA_NAME = os.getenv("LAKEBASE_SCHEMA_NAME", "zerobus_sdp")
LAKEBASE_PORT = int(os.getenv("LAKEBASE_PORT", "5432"))
