# Granting Lakebase Permissions to App Service Principal

## Problem

Each time a Databricks App is deployed, it gets a new Service Principal ID. This Service Principal needs permissions to query the Lakebase database (`zerobus_sdp`), but these permissions don't persist across deployments.

## Solution

After each deployment, run these SQL commands to grant the necessary permissions.

### Step 1: Get the App Service Principal Client ID

```bash
databricks apps get o11y-jmr --output json | grep service_principal_client_id
```

This will show something like:
```json
"service_principal_client_id": "5ff7efef-9137-4206-9d9c-e58dd3176ced",
```

Copy this UUID (not the numeric service_principal_id).

### Step 2: Grant Permissions via Lakebase PostgreSQL

Run these SQL commands in Lakebase query editor:

```sql
-- Replace <SP_CLIENT_ID> with the actual service principal client ID from Step 1
-- Note: Use the service_principal_client_id (UUID format), not the service_principal_id (numeric)

-- Grant CONNECT permission on the database
GRANT CONNECT ON DATABASE zerobus_sdp TO "<SP_CLIENT_ID>";

-- Grant USAGE permission on the schema
GRANT USAGE ON SCHEMA zerobus_sdp TO "<SP_CLIENT_ID>";

-- Grant SELECT permission on all existing tables in the schema
GRANT SELECT ON ALL TABLES IN SCHEMA zerobus_sdp TO "<SP_CLIENT_ID>";

-- Grant SELECT permission on future tables (optional)
ALTER DEFAULT PRIVILEGES IN SCHEMA zerobus_sdp GRANT SELECT ON TABLES TO "<SP_CLIENT_ID>";
```

### Example:

```sql
-- Using service_principal_client_id: 5ff7efef-9137-4206-9d9c-e58dd3176ced
GRANT CONNECT ON DATABASE zerobus_sdp TO "5ff7efef-9137-4206-9d9c-e58dd3176ced";
GRANT USAGE ON SCHEMA zerobus_sdp TO "5ff7efef-9137-4206-9d9c-e58dd3176ced";
GRANT SELECT ON ALL TABLES IN SCHEMA zerobus_sdp TO "5ff7efef-9137-4206-9d9c-e58dd3176ced";
ALTER DEFAULT PRIVILEGES IN SCHEMA zerobus_sdp GRANT SELECT ON TABLES TO "5ff7efef-9137-4206-9d9c-e58dd3176ced";
```

### Step 3: Verify Permissions

Test the app by accessing: https://o11y-jmr-1351565862180944.aws.databricksapps.com

The app should now be able to query trace and service data.

## Automated Solution (Future)

To avoid manual steps, consider:

1. **Use a fixed Service Principal**: Configure the app to use a specific service principal instead of auto-generated ones
2. **Post-deployment hook**: Add a `databricks bundle run` post-deployment script
3. **Lakebase roles**: Create a dedicated role with read permissions and grant it to the app

## Troubleshooting

If you see `permission denied for schema zerobus_sdp`:
- Verify the Service Principal Client ID (UUID format) is correct
- Ensure you ran all four GRANT statements (CONNECT, USAGE, SELECT, ALTER DEFAULT)
- Check that you're connected to the correct database (`zerobus_sdp`)
- Make sure you're using double quotes around the UUID, not backticks

If tables are still inaccessible:
- The schema might have been recreated - re-run the grants
- Check if DEFAULT PRIVILEGES were applied correctly
- Verify the service principal exists as a PostgreSQL role
