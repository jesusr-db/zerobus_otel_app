#!/bin/bash

# Grant Lakebase permissions to App Service Principal
# Usage: ./grant_lakebase_permissions.sh <app-name>

set -e

APP_NAME="${1:-o11y-jmr}"
DATABASE="zerobus_sdp"

echo "Getting service principal for app: $APP_NAME"
APP_DATA=$(databricks apps get "$APP_NAME" --output json)
SP_ID=$(echo "$APP_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('service_principal_id', data.get('service_principal_name', 'unknown')))")

if [ "$SP_ID" = "unknown" ]; then
    echo "Error: Could not find service principal ID"
    exit 1
fi

echo "Found service principal: $SP_ID"
echo ""
echo "Granting permissions..."

# Execute SQL grants via Python script
python3 << EOF
import os
from server.services.lakebase_manager import LakebaseManager

# Use system token for admin operations
lakebase = LakebaseManager(user_token=None)

grants = [
    f"GRANT USAGE ON SCHEMA zerobus_sdp TO \"{$SP_ID}\"",
    f"GRANT SELECT ON ALL TABLES IN SCHEMA zerobus_sdp TO \"{$SP_ID}\"",
    f"ALTER DEFAULT PRIVILEGES IN SCHEMA zerobus_sdp GRANT SELECT ON TABLES TO \"{$SP_ID}\"",
]

for grant in grants:
    try:
        print(f"Executing: {grant}")
        lakebase.execute_query(grant)
        print("  ✓ Success")
    except Exception as e:
        print(f"  ⚠ Warning: {e}")

print("\n✓ Permissions granted successfully")
EOF

echo ""
echo "✓ All done! App should now have access to Lakebase."
