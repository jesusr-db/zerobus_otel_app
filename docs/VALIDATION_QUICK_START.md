# Lakebase Validation Quick Start

## 🚀 5-Minute Validation Checklist

### 1️⃣ Start Dev Server
```bash
./watch.sh
# Wait for: "Application startup complete"
```

### 2️⃣ Test Connectivity (30 seconds)
```bash
curl http://localhost:8000/api/lakebase-validation/connectivity | jq .overall_status
# Expected: true
```

**✅ Success Indicators in Logs:**
```
✅ SQL Warehouse connected: {'warehouse_id': '...', 'warehouse_name': '...', 'status': 'RUNNING'}
✅ Lakebase connected: {'instance_name': 'zerobus-dev', ...}
✅ Test query result: [{'test': 1}]
✅ Validation suite passed - both backends are accessible
```

**❌ If Failed:**
- Check `LAKEBASE_HOST` in app.yml
- Check `DATABRICKS_HOST` and credentials
- Look for error details in logs

---

### 3️⃣ Test Services Query (1 minute)
```bash
curl "http://localhost:8000/api/lakebase-validation/test-services-query?time_range=1h" | jq '.results.match'
# Expected: true
```

**✅ Success Indicators in Logs:**
```
================================================================================
Query Conversion Validation: services-list-1h
================================================================================
📝 Original Spark SQL Query:
--------------------------------------------------------------------------------
  1 | SELECT...
  2 | FROM traces_assembled_silver t
  3 | LATERAL VIEW explode(span_details) AS span
...
--------------------------------------------------------------------------------
🔄 Converted PostgreSQL Query:
--------------------------------------------------------------------------------
  1 | SELECT...
  2 | FROM traces_assembled_synced t
  3 | CROSS JOIN LATERAL unnest(span_details) AS span(span)
...
--------------------------------------------------------------------------------
🔍 Detected Query Changes:
  • LATERAL VIEW explode → CROSS JOIN LATERAL unnest
  • Table names: _silver → _synced
✅ Query conversion successful
================================================================================

================================================================================
Result Comparison: services-list-1h
================================================================================
📊 Executing on SQL Warehouse...
✅ Warehouse returned 5 rows
Warehouse Sample Results (showing 3 of 5):
--------------------------------------------------------------------------------
Row 1:
  service_name: api-gateway
  request_count: 1234
  avg_duration: 45.6
...
📊 Executing on Lakebase...
✅ Lakebase returned 5 rows
Lakebase Sample Results (showing 3 of 5):
--------------------------------------------------------------------------------
Row 1:
  service_name: api-gateway
  request_count: 1234
  avg_duration: 45.6
...
🔍 Comparing Results...
✅ Results match!
================================================================================
```

**❌ If Results Don't Match:**
Check `.differences` in response:
```bash
curl "http://localhost:8000/api/lakebase-validation/test-services-query?time_range=1h" | jq '.results.differences'
```

Common issues:
- Row count mismatch → Data sync lag
- Column differences → SQL conversion issue
- Value differences → Check data types

---

### 4️⃣ Monitor Real Query Execution (ongoing)

**Watch logs for query execution:**
```bash
tail -f /tmp/databricks-app-watch.log | grep -A 15 "Executing Lakebase Query"
```

**Successful Query Pattern:**
```
================================================================================
Executing Lakebase Query
Instance: zerobus-dev
Database: databricks_postgres
Schema: zerobus_sdp.zerobus_sdp
--------------------------------------------------------------------------------
(query preview in DEBUG mode)
--------------------------------------------------------------------------------
✅ Query succeeded
   Rows returned: 42
   Columns: ['service_name', 'latency_p50', 'request_count', ...]
   Execution time: 0.156s
================================================================================
```

**Failed Query Pattern:**
```
================================================================================
❌ Lakebase Query Failed
   Instance: zerobus-dev
   Database: databricks_postgres
   Error: syntax error at or near "explode"
   Execution time: 0.023s
--------------------------------------------------------------------------------
Failed Query:
SELECT ... FROM traces_assembled_synced
LATERAL VIEW explode(span_details) AS span  <-- NOT CONVERTED!
--------------------------------------------------------------------------------
Full traceback:
...
================================================================================
```

---

## 📊 Key Metrics to Watch

### Query Performance
| Metric | Good | Warning | Action |
|--------|------|---------|--------|
| Execution time | < 0.5s | 0.5s - 2s | > 2s - investigate |
| Row count match | ✅ 100% | ⚠️ 95-99% | ❌ < 95% - data issue |
| Error rate | 0% | < 1% | > 1% - fix queries |

### Connection Health
```bash
# Check OAuth token refresh (every 15 min)
tail -f /tmp/databricks-app-watch.log | grep "Refreshing PostgreSQL OAuth token"

# Expected every 15 minutes:
INFO: Refreshing PostgreSQL OAuth token for instance: zerobus-dev
```

---

## 🐛 Quick Troubleshooting

### "Connection refused"
```bash
# Check LAKEBASE_HOST
grep LAKEBASE_HOST app.yml
# Should show: instance-xxxx.database.cloud.databricks.com
```

### "OAuth token expired"
```bash
# Check token refresh logs
grep "Refreshing PostgreSQL OAuth token" /tmp/databricks-app-watch.log | tail -5
# Should see entries within last 15 minutes
```

### "Table does not exist"
```bash
# Check table name conversion
curl -X POST "http://localhost:8000/api/lakebase-validation/validate-query?endpoint_name=test&spark_query=SELECT%20*%20FROM%20traces_silver" | jq '.postgres_query'
# Should show: traces_silver_synced (with _synced suffix)
```

### "Results don't match"
```bash
# Get detailed differences
curl -X POST "http://localhost:8000/api/lakebase-validation/compare-results?endpoint_name=debug&spark_query=<query>&sample_limit=10" | jq '.differences'

# Common fixes:
# 1. Row count differs → Check data sync status
# 2. Column names differ → Update sql_converter.py
# 3. Values differ → Check data types and precision
```

---

## 🎯 Ready to Migrate?

**Pre-flight checklist:**
- ✅ Connectivity test passes
- ✅ Services query test passes
- ✅ Results match between backends
- ✅ No errors in logs for 5+ minutes
- ✅ Query execution times < 1s

**Go/No-Go Decision:**
```bash
# Run full validation
curl http://localhost:8000/api/lakebase-validation/connectivity | jq .overall_status
curl "http://localhost:8000/api/lakebase-validation/test-services-query?time_range=1h" | jq '.results.match'

# Both return true? ✅ GO for migration!
# Either returns false? ❌ NO-GO - investigate first
```

---

## 📞 Getting Help

**Check logs first:**
```bash
# Full logs
tail -100 /tmp/databricks-app-watch.log

# Just errors
tail -100 /tmp/databricks-app-watch.log | grep ERROR

# Just Lakebase activity
tail -100 /tmp/databricks-app-watch.log | grep Lakebase
```

**Common log search patterns:**
```bash
# Find all query failures
grep "❌ Lakebase Query Failed" /tmp/databricks-app-watch.log

# Find all successful queries with timing
grep "Query succeeded" /tmp/databricks-app-watch.log

# Find conversion issues
grep "Query conversion" /tmp/databricks-app-watch.log
```

---

## 🚀 Next: Apply to Your Routers

Once validation passes, apply this pattern to your routers:

```python
from server.services.warehouse_manager import WarehouseManager
from server.services.lakebase_manager import LakebaseManager
from server.services.sql_converter import convert_spark_to_postgres
from server.config import DATA_BACKEND

def get_data_manager(user_token):
    if DATA_BACKEND == "lakebase":
        return LakebaseManager(user_token=user_token)
    else:
        return WarehouseManager(user_token=user_token)

# In your endpoint:
data_manager = get_data_manager(user_token)
query = convert_spark_to_postgres(spark_query) if DATA_BACKEND == "lakebase" else spark_query
results = data_manager.execute_query(query)
```

**All logs will automatically show detailed query execution info!**
