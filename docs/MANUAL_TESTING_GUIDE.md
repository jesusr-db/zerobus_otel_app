# Manual Testing Guide - Lakebase Validation

## 🎯 Testing in Arc Browser

### Prerequisites
✅ Lakebase permissions granted to Service Principal
✅ App deployed and running
✅ Arc browser (or any browser)

---

## 📋 Test Checklist

### Test 1: Connectivity Validation ✅

**URL**: 
```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/connectivity
```

**Expected Result**:
```json
{
  "validation_timestamp": "2025-12-29T...",
  "connectivity": {
    "warehouse": {
      "connected": true,
      "error": null,
      "info": {
        "warehouse_id": "...",
        "warehouse_name": "...",
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
        "host": "instance-6125d6d9-44a4-46b7-a5ff-6db65cbf60c5.database.cloud.databricks.com",
        "port": 5432,
        "table_prefix": "zerobus_sdp.zerobus_sdp"
      },
      "test_query_result": [{"test": 1}]
    }
  },
  "overall_status": true
}
```

**✅ Success Indicators**:
- `overall_status: true`
- Both `warehouse.connected: true` and `lakebase.connected: true`
- `test_query_result` shows data

**❌ Failure Signs**:
- `overall_status: false`
- Error messages in `error` fields
- Connection failures

---

### Test 2: Services Query Comparison ✅

**URL**:
```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/test-services-query?time_range=1h
```

**Expected Result**:
```json
{
  "test": "services-list",
  "time_range": "1h",
  "results": {
    "endpoint": "services-list-1h",
    "timestamp": "2025-12-29T...",
    "warehouse": {
      "success": true,
      "row_count": 5,
      "error": null,
      "sample_rows": [
        {
          "service_name": "api-gateway",
          "request_count": 1234,
          "avg_duration": 45.6
        },
        ...
      ]
    },
    "lakebase": {
      "success": true,
      "row_count": 5,
      "error": null,
      "sample_rows": [
        {
          "service_name": "api-gateway",
          "request_count": 1234,
          "avg_duration": 45.6
        },
        ...
      ]
    },
    "match": true,
    "differences": []
  }
}
```

**✅ Success Indicators**:
- `warehouse.success: true`
- `lakebase.success: true`
- `match: true`
- `differences: []` (empty array = perfect match)
- Same row counts
- Same data in sample_rows

**❌ Failure Signs**:
- `match: false`
- Non-empty `differences` array
- Different row counts
- Errors in either backend

---

### Test 3: View Detailed Logs 📊

**URL**:
```
https://o11y-jmr-1351565862180944.aws.databricksapps.com/logz
```

**What to Look For**:

#### ✅ Successful Lakebase Connection
```
================================================================================
Testing Lakebase Connectivity
================================================================================
✅ Lakebase connected: {
    'instance_name': 'zerobus-dev',
    'database_name': 'databricks_postgres',
    'catalog_name': 'zerobus_sdp',
    'schema_name': 'zerobus_sdp',
    'host': 'instance-6125d6d9-44a4-46b7-a5ff-6db65cbf60c5.database.cloud.databricks.com',
    'port': 5432
}
✅ Test query result: [{'test': 1}]
================================================================================
```

#### ✅ Query Conversion Logging
```
================================================================================
Query Conversion Validation: services-list-1h
================================================================================
📝 Original Spark SQL Query:
--------------------------------------------------------------------------------
  1 | SELECT 
  2 |   span.service_name,
  3 |   COUNT(*) as request_count
  4 | FROM traces_assembled_silver t
  5 | LATERAL VIEW explode(span_details) AS span
  6 | WHERE t.trace_start >= NOW() - INTERVAL 1 hour
  7 | GROUP BY span.service_name
--------------------------------------------------------------------------------
🔄 Converted PostgreSQL Query:
--------------------------------------------------------------------------------
  1 | SELECT 
  2 |   span.service_name,
  3 |   COUNT(*) as request_count
  4 | FROM traces_assembled_synced t
  5 | CROSS JOIN LATERAL unnest(span_details) AS span(span)
  6 | WHERE t.trace_start >= NOW() - INTERVAL '1 hour'
  7 | GROUP BY span.service_name
--------------------------------------------------------------------------------
🔍 Detected Query Changes:
  • LATERAL VIEW explode → CROSS JOIN LATERAL unnest
  • Table names: _silver → _synced
  • INTERVAL syntax quoted for PostgreSQL
✅ Query conversion successful
================================================================================
```

#### ✅ Result Comparison Logging
```
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
Row 2:
  service_name: auth-service
  request_count: 567
  avg_duration: 23.4
Row 3:
  service_name: payment-service
  request_count: 890
  avg_duration: 78.9
--------------------------------------------------------------------------------
📊 Executing on Lakebase...
✅ Lakebase returned 5 rows
Lakebase Sample Results (showing 3 of 5):
--------------------------------------------------------------------------------
Row 1:
  service_name: api-gateway
  request_count: 1234
  avg_duration: 45.6
Row 2:
  service_name: auth-service
  request_count: 567
  avg_duration: 23.4
Row 3:
  service_name: payment-service
  request_count: 890
  avg_duration: 78.9
--------------------------------------------------------------------------------
🔍 Comparing Results...
✅ Results match!
================================================================================
```

#### ✅ Query Execution Performance
```
================================================================================
Executing Lakebase Query
Instance: zerobus-dev
Database: databricks_postgres
Schema: zerobus_sdp.zerobus_sdp
--------------------------------------------------------------------------------
✅ Query succeeded
   Rows returned: 5
   Columns: ['service_name', 'request_count', 'avg_duration']
   Execution time: 0.156s  ← Look for fast execution times!
================================================================================
```

---

## 🎯 Success Criteria

### ✅ All Tests Pass When:

1. **Connectivity Test**:
   - ✅ `overall_status: true`
   - ✅ Both backends connected
   - ✅ Test query returns data

2. **Services Query Test**:
   - ✅ Both backends return data
   - ✅ Results match (`match: true`)
   - ✅ No differences
   - ✅ Same row counts

3. **Logs Show**:
   - ✅ Successful connections
   - ✅ Query conversions working
   - ✅ Fast execution times (< 1s)
   - ✅ No errors or exceptions

---

## 📊 What This Validates

### ✅ Infrastructure
- Databricks Apps deployment working
- OAuth authentication configured
- Environment variables loaded
- Python dependencies installed

### ✅ Connectivity
- SQL Warehouse accessible
- Lakebase instance accessible
- OAuth token generation working
- Network connectivity good

### ✅ Query Conversion
- Spark SQL → PostgreSQL conversion working
- Table name mapping (_silver → _synced) working
- Syntax conversions (LATERAL VIEW, INTERVAL) working
- No syntax errors

### ✅ Data Accuracy
- Both backends return same data
- Row counts match
- Values match
- No data loss or corruption

### ✅ Performance
- Lakebase queries fast (should be < 1s)
- No timeouts
- Connection pooling working
- OAuth token refresh working

---

## 🐛 Troubleshooting

### If Connectivity Test Fails:

**Check**:
1. Service Principal permissions (already granted ✅)
2. Lakebase instance running
3. Network connectivity
4. Environment variables in app.yml

**Look for in logs**:
- `FATAL: role "..." does not exist` → Permission issue
- `connection refused` → Network/instance issue
- `timeout` → Performance/network issue

### If Query Test Fails:

**Check**:
1. Tables exist in Lakebase (`*_synced` tables)
2. Data synced to Lakebase
3. SQL syntax conversion working
4. Query conversion logs for errors

**Look for in logs**:
- `relation "..." does not exist` → Table missing
- `syntax error` → SQL conversion issue
- `column "..." does not exist` → Schema mismatch

### If Results Don't Match:

**Check**:
1. Data sync lag (Lakebase may be behind)
2. Schema differences
3. Query conversion correctness

**Look for in logs**:
- Row count differences
- Column name differences
- Value differences (check `.differences` array)

---

## 🚀 Next Steps After Validation

Once all tests pass:

1. ✅ **Document Results** - Screenshot/save test results
2. ✅ **Update Routers** - Apply Lakebase pattern to production endpoints
3. ✅ **Monitor Performance** - Track query execution times
4. ✅ **Plan Rollout** - Decide migration timeline
5. ✅ **Setup Monitoring** - Configure alerts for Lakebase health

---

## 📝 Test Results Template

**Date**: ___________
**Tester**: ___________

| Test | Status | Notes |
|------|--------|-------|
| Connectivity Test | ☐ Pass ☐ Fail | |
| Services Query Test | ☐ Pass ☐ Fail | |
| Logs Review | ☐ Pass ☐ Fail | |
| Performance Check | ☐ Pass ☐ Fail | |

**Overall Result**: ☐ All Tests Pass ☐ Some Failures

**Issues Found**:
-
-

**Next Actions**:
-
-
