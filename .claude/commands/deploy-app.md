# Deploy App using Databricks Asset Bundles (DABs)

Deploy the observability app to Databricks using DABs workflow.

## Arguments
- `$ARGUMENTS` - Target environment (default: dev). Options: dev, dogfood, prod

## Workflow

Execute these steps in order:

### 1. Set Target
```bash
TARGET="${ARGUMENTS:-dev}"
echo "Deploying to target: $TARGET"
```

### 2. Rebuild Frontend
```bash
cd client && bun run build
```

### 3. Validate Bundle
```bash
databricks bundle validate -t $TARGET
```

### 4. Deploy Bundle
```bash
databricks bundle deploy -t $TARGET
```

### 5. Get App Status
```bash
databricks apps get o11y-jmr --output json | python3 -c "
import sys, json
app = json.load(sys.stdin)
print(f\"App: {app['name']}\")
print(f\"URL: {app['url']}\")
print(f\"Status: {app.get('app_status', {}).get('state', 'UNKNOWN')}\")
print(f\"Compute: {app.get('compute_status', {}).get('state', 'UNKNOWN')}\")
print(f\"Deployment: {app.get('active_deployment', {}).get('status', {}).get('state', 'UNKNOWN')}\")
"
```

### 6. Check if App is Running
If the app status is not RUNNING, start it:
```bash
databricks apps start o11y-jmr
```

### 7. Open App URL
```bash
open "https://o11y-jmr-1351565862180944.aws.databricksapps.com"
```

## Post-Deployment Verification

After deployment, verify the app is working:
1. Check that the app URL loads in the browser
2. Verify API endpoints respond (may require OAuth)
3. Check for any console errors in the browser

## Troubleshooting

If deployment fails:
- Check `databricks bundle validate` output for configuration errors
- Check that the target exists in `databricks.yml`

If app fails to start:
- Check app logs via Databricks UI
- Verify environment variables are set correctly in `resources/app.yml`
- Check Lakebase connectivity and permissions
