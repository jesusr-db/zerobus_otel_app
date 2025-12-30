# Lakebase Validation & Testing Guide

## Overview

Comprehensive validation system for testing Lakebase migration with detailed logging and query comparison.

## Validation Endpoints

All validation endpoints are prefixed with `/api/lakebase-validation/`

### 1. **Connectivity Test**
**Endpoint**: `GET /api/lakebase-validation/connectivity`

Tests connections to both SQL Warehouse and Lakebase with detailed configuration info.

```bash
# Local testing
curl http://localhost:8000/api/lakebase-validation/connectivity | jq

# Deployed app testing
python dba_client.py <app-url> /api/lakebase-validation/connectivity
```

**Response**:
```json
{
  "validation_timestamp": "2025-01-15T10:30:00.123456",
  "connectivity": {
    "warehouse": {
      "connected": true,
      "error": null,
      "info": {
        "warehouse_id": "abc123",
        "warehouse_name": "Serverless Starter Warehouse",
        "status": "RUNNING"
      }
    },
    "lakebase": {
      "connected": true,
      "error": null,
      "info": {
        "instance_name": "zerobus-dev",
        "database_name": "databricks_postgres",
        "catalog_name": "zerobus_sdp",
        "schema_name": "zerobus_sdp",
        "host": "instance-xxx.database.cloud.databricks.com",
        "port": 5432,
        "table_prefix": "zerobus_sdp.zerobus_sdp"
      },
      "test_query_result": [{"test": 1}]
    }
  },
  "overall_status": true
}
```

### 2. **Query Conversion Validation**
**Endpoint**: `POST /api/lakebase-validation/validate-query`

Validates Spark SQL → PostgreSQL conversion and shows detected changes.

```bash
# Example: Validate services list query
curl -X POST "http://localhost:8000/api/lakebase-validation/validate-query?endpoint_name=services-list&spark_query=SELECT%20*%20FROM%20traces" | jq
```

**What it logs**:
- ✅ Original Spark SQL query (line by line)
- ✅ Converted PostgreSQL query (line by line)
- ✅ Detected conversions:
  - `LATERAL VIEW explode` → `CROSS JOIN LATERAL unnest`
  - `INTERVAL` quoting changes
  - `array_contains` → `ANY` operator
  - Table name changes (`_silver` → `_synced`)

### 3. **Result Comparison**
**Endpoint**: `POST /api/lakebase-validation/compare-results`

Executes query on BOTH backends and compares results.

```bash
# Compare results from both backends
curl -X POST "http://localhost:8000/api/lakebase-validation/compare-results?endpoint_name=test&spark_query=SELECT%20COUNT(*)%20FROM%20traces&sample_limit=5" | jq
```

**Response**:
```json
{
  "endpoint": "test",
  "timestamp": "2025-01-15T10:30:00.123456",
  "warehouse": {
    "success": true,
    "row_count": 10,
    "error": null,
    "sample_rows": [{"service_name": "api", "count": 100}, ...]
  },
  "lakebase": {
    "success": true,
    "row_count": 10,
    "error": null,
    "sample_rows": [{"service_name": "api", "count": 100}, ...]
  },
  "match": true,
  "differences": []
}
```

### 4. **Services Query Test**
**Endpoint**: `GET /api/lakebase-validation/test-services-query?time_range=1h`

Convenience endpoint that tests the main services list query.

```bash
# Test with 1 hour time range
curl "http://localhost:8000/api/lakebase-validation/test-services-query?time_range=1h" | jq

# Test with 24 hour time range
curl "http://localhost:8000/api/lakebase-validation/test-services-query?time_range=24h" | jq
```

## Enhanced Logging

### Log Levels
Set in `server/app.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Shows all query details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Lakebase Query Logging Format

Every Lakebase query logs:

```
================================================================================
Executing Lakebase Query
Instance: zerobus-dev
Database: databricks_postgres
Schema: zerobus_sdp.zerobus_sdp
--------------------------------------------------------------------------------
Query:
SELECT service_name, COUNT(*) as count
FROM zerobus_sdp.zerobus_sdp.traces_assembled_synced
WHERE trace_start >= NOW() - INTERVAL '1 hour'
GROUP BY service_name
--------------------------------------------------------------------------------
✅ Query succeeded
   Rows returned: 5
   Columns: ['service_name', 'count']
   Execution time: 0.234s
================================================================================
```

### Error Logging Format

Query failures log:

```
================================================================================
❌ Lakebase Query Failed
   Instance: zerobus-dev
   Database: databricks_postgres
   Error: relation "traces_assembled_synced" does not exist
   Execution time: 0.045s
--------------------------------------------------------------------------------
Failed Query:
SELECT * FROM traces_assembled_synced
================================================================================
Full traceback:
...
```

## Testing Workflow

### Step 1: Test Connectivity
```bash
# Start dev server
./watch.sh

# Test connectivity
curl http://localhost:8000/api/lakebase-validation/connectivity | jq .overall_status

# Expected: true
```

**Check logs for**:
- ✅ "SQL Warehouse connected"
- ✅ "Lakebase connected"
- ✅ "Test query result: [{'test': 1}]"

### Step 2: Validate Query Conversion
```bash
# Test services query conversion
curl -X POST "http://localhost:8000/api/lakebase-validation/validate-query?endpoint_name=services&spark_query=$(cat <<EOF | jq -sRr @uri
SELECT 
  span.service_name
FROM traces_assembled_silver t
LATERAL VIEW explode(span_details) AS span
WHERE array_contains(services_involved, 'api')
EOF
)" | jq
```

**Check logs for**:
- 📝 Original Spark SQL Query (line numbered)
- 🔄 Converted PostgreSQL Query (line numbered)
- 🔍 Detected Query Changes:
  - LATERAL VIEW explode → CROSS JOIN LATERAL unnest
  - array_contains → ANY operator
  - Table names: _silver → _synced

### Step 3: Compare Results
```bash
# Run comparison on services query
curl "http://localhost:8000/api/lakebase-validation/test-services-query?time_range=1h" | jq
```

**Check response for**:
- `.warehouse.success: true`
- `.lakebase.success: true`
- `.match: true`
- `.differences: []` (empty = perfect match)

**Check logs for**:
- 📊 Executing on SQL Warehouse...
- ✅ Warehouse returned X rows
- Warehouse Sample Results (showing Y rows)
- 📊 Executing on Lakebase...
- ✅ Lakebase returned X rows
- Lakebase Sample Results (showing Y rows)
- 🔍 Comparing Results...
- ✅ Results match!

### Step 4: Test Individual Endpoints

For each router endpoint you want to migrate:

1. Extract the Spark SQL query from the router
2. Test conversion:
   ```bash
   curl -X POST "http://localhost:8000/api/lakebase-validation/validate-query?endpoint_name=my-endpoint&spark_query=<encoded-query>"
   ```
3. Compare results:
   ```bash
   curl -X POST "http://localhost:8000/api/lakebase-validation/compare-results?endpoint_name=my-endpoint&spark_query=<encoded-query>&sample_limit=5"
   ```
4. Fix any differences in `sql_converter.py`
5. Re-test until `.match: true`

## Common Issues & Solutions

### Issue: "LAKEBASE_HOST environment variable is required"
**Solution**: Set in `app.yml`:
```yaml
env:
  - name: LAKEBASE_HOST
    value: instance-xxx.database.cloud.databricks.com
```

### Issue: "relation does not exist"
**Solution**: Table names need `_synced` suffix. Update `sql_converter.py`:
```python
replacements = {
    'your_table_name': 'your_table_name_synced',
}
```

### Issue: OAuth token expired
**Solution**: LakebaseManager auto-refreshes every 15 min. Check logs for:
```
INFO: Refreshing PostgreSQL OAuth token for instance: zerobus-dev
```

### Issue: Results don't match
**Check**:
1. Row count difference → Data sync lag or missing data in Lakebase
2. Column name difference → SQL conversion issue, check query converter
3. Value difference → Data type conversion or precision issue

**Debug**:
```bash
# Get detailed comparison
curl -X POST "http://localhost:8000/api/lakebase-validation/compare-results?endpoint_name=debug&spark_query=<query>&sample_limit=10" | jq .differences
```

## Performance Monitoring

### Query Execution Time

All queries log execution time:
```
Execution time: 0.234s
```

Compare Warehouse vs Lakebase times:
- **Warehouse**: Typically 0.5s - 5s (depends on warehouse size)
- **Lakebase**: Typically 0.1s - 0.5s (PostgreSQL OLTP optimized)

### Expected Performance Gains
- **Simple queries**: 2-5x faster on Lakebase
- **Complex aggregations**: 1.5-3x faster on Lakebase
- **High concurrency**: Better on Lakebase (connection pooling)

## Integration Testing Script

Create a test script to validate all endpoints:

```python
# test_lakebase_migration.py
import requests
import json

BASE_URL = "http://localhost:8000/api/lakebase-validation"

def test_connectivity():
    response = requests.get(f"{BASE_URL}/connectivity")
    assert response.json()["overall_status"] == True
    print("✅ Connectivity test passed")

def test_services_query():
    response = requests.get(f"{BASE_URL}/test-services-query?time_range=1h")
    result = response.json()
    assert result["results"]["match"] == True
    print("✅ Services query test passed")

if __name__ == "__main__":
    test_connectivity()
    test_services_query()
    print("✅ All validation tests passed!")
```

Run with:
```bash
python test_lakebase_migration.py
```

## Deployment Validation

After deploying with DABS:

```bash
# Deploy
databricks bundle deploy
databricks bundle run o11y_jmr_app

# Get app URL
APP_URL=$(databricks apps get o11y-jmr --output json | jq -r .url)

# Test connectivity
python dba_client.py $APP_URL /api/lakebase-validation/connectivity

# Monitor logs for issues
python dba_logz.py $APP_URL --search "Lakebase|ERROR" --duration 60
```

## Next Steps

1. ✅ Test connectivity
2. ✅ Validate query conversions
3. ✅ Compare results for all endpoints
4. 🚀 Deploy to dev environment
5. 📊 Monitor performance for 24 hours
6. ✅ Deploy to production

---

**Need help?** Check logs with:
```bash
tail -f /tmp/databricks-app-watch.log | grep -A 10 -B 10 "Lakebase\|ERROR"
```
