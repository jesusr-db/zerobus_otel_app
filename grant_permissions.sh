#!/bin/bash
set -e

# Grant Lakebase permissions to deployed app's service principal
# This script must be run from your local machine with Databricks CLI configured

APP_NAME="${1:-o11y-jmr}"
LAKEBASE_INSTANCE="${2:-zerobus-dev}"
LAKEBASE_DATABASE="${3:-zerobus_sdp}"
LAKEBASE_SCHEMA="${4:-zerobus_sdp}"

echo "=========================================="
echo "Grant Lakebase Permissions"
echo "=========================================="
echo "App: $APP_NAME"
echo "Instance: $LAKEBASE_INSTANCE"
echo "Database: $LAKEBASE_DATABASE"
echo "Schema: $LAKEBASE_SCHEMA"
echo ""

# Get service principal from app
echo "Getting service principal from app..."
SP_CLIENT_ID=$(databricks apps get "$APP_NAME" --output json | python3 -c "import sys, json; print(json.load(sys.stdin)['service_principal_client_id'])")

if [ -z "$SP_CLIENT_ID" ]; then
    echo "ERROR: Could not get service principal client ID"
    exit 1
fi

echo "Service Principal Client ID: $SP_CLIENT_ID"
echo ""

# Generate SQL commands
SQL_FILE="/tmp/grant_lakebase_permissions_${SP_CLIENT_ID}.sql"

cat > "$SQL_FILE" <<EOF
-- Grant Lakebase permissions to app service principal
-- Generated on $(date)
-- Service Principal: $SP_CLIENT_ID

GRANT CONNECT ON DATABASE ${LAKEBASE_DATABASE} TO "${SP_CLIENT_ID}";
GRANT USAGE ON SCHEMA ${LAKEBASE_SCHEMA} TO "${SP_CLIENT_ID}";
GRANT SELECT ON ALL TABLES IN SCHEMA ${LAKEBASE_SCHEMA} TO "${SP_CLIENT_ID}";
ALTER DEFAULT PRIVILEGES IN SCHEMA ${LAKEBASE_SCHEMA} GRANT SELECT ON TABLES TO "${SP_CLIENT_ID}";
EOF

echo "=========================================="
echo "SQL commands generated at: $SQL_FILE"
echo "=========================================="
echo ""
cat "$SQL_FILE"
echo ""
echo "=========================================="
echo "NEXT STEPS:"
echo "=========================================="
echo "1. Open Lakebase query editor"
echo "2. Connect to database: $LAKEBASE_DATABASE"
echo "3. Copy and run the SQL commands above"
echo ""
echo "Or copy the file contents:"
echo "  cat $SQL_FILE | pbcopy"
echo "=========================================="
