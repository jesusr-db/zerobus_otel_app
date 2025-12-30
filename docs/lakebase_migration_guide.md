# Lakebase Migration Guide

## Overview

This guide documents the migration from Databricks SQL Warehouse to Lakebase (managed PostgreSQL) for improved performance in the observability application.

## Architecture Changes

### Before (SQL Warehouse)
- **Backend**: Databricks SQL Warehouse
- **Connection**: Databricks SDK `statement_execution` API
- **Query Language**: Spark SQL
- **Tables**: Unity Catalog tables (`traces_assembled_silver`, `traces_silver`, etc.)

### After (Lakebase)
- **Backend**: Lakebase managed PostgreSQL (`zerobus-dev` instance)
- **Connection**: SQLAlchemy + psycopg2 with OAuth token refresh
- **Query Language**: PostgreSQL SQL
- **Tables**: Synced tables (`traces_assembled_synced`, `traces_silver_synced`, etc.)

## Implementation Components

### 1. LakebaseManager (`server/services/lakebase_manager.py`)
- Manages PostgreSQL connections with OAuth token refresh
- Uses SQLAlchemy connection pooling
- Automatically refreshes Databricks OAuth tokens every 15 minutes
- Provides `execute_query()` method compatible with WarehouseManager

### 2. SQL Query Converter (`server/services/sql_converter.py`)
Handles Spark SQL → PostgreSQL conversions:
- `LATERAL VIEW explode()` → `CROSS JOIN LATERAL unnest()`
- `INTERVAL 1 HOUR` → `INTERVAL '1 hour'`
- `array_contains(arr, val)` → `val = ANY(arr)`
- Table names: `_silver` → `_synced`

### 3. Configuration (`server/config.py`)
New environment variables:
- `DATA_BACKEND`: "warehouse" or "lakebase"
- `LAKEBASE_INSTANCE_NAME`: "zerobus-dev"
- `LAKEBASE_HOST`: Lakebase instance hostname
- `LAKEBASE_CATALOG_NAME`: "zerobus_sdp"
- `LAKEBASE_SCHEMA_NAME`: "zerobus_sdp"

### 4. Router Updates
Example in `server/routers/services_lakebase_example.py`:
- Factory function `get_data_manager()` selects backend
- Queries converted with `convert_spark_to_postgres()` when using Lakebase
- Backward compatible with SQL Warehouse

## Deployment Configuration

### app.yml Changes
```yaml
env:
  - name: DATA_BACKEND
    value: lakebase
  - name: LAKEBASE_INSTANCE_NAME
    value: zerobus-dev
  - name: LAKEBASE_HOST
    value: ${resources.lakebase-instance.host}

resources:
  - name: lakebase-instance
    database_instance:
      id: zerobus-dev
      permission: CAN_USE
```

### DABS Configuration (resources/app.yml)
```yaml
resources:
  apps:
    o11y_jmr_app:
      resources:
        - name: lakebase-instance
          database_instance:
            id: zerobus-dev
            permission: CAN_USE
```

## Migration Steps

### Phase 1: Setup ✅
1. ✅ Add PostgreSQL dependencies (sqlalchemy, psycopg2-binary)
2. ✅ Create LakebaseManager class
3. ✅ Create SQL query converter utility
4. ✅ Update configuration files

### Phase 2: Router Migration (In Progress)
1. Update `server/routers/services.py`:
   - Add `get_data_manager()` factory function
   - Convert Spark SQL queries for Lakebase
   - Test `/api/services/list` endpoint

2. Update remaining routers:
   - `warehouse.py` (warehouse info endpoint)
   - Any other routers using SQL queries

### Phase 3: Testing
1. **Local Testing**:
   ```bash
   # Set environment for Lakebase
   export DATA_BACKEND=lakebase
   export LAKEBASE_HOST=<instance-host>
   
   # Run development server
   ./watch.sh
   
   # Test endpoints
   curl http://localhost:8000/api/services/list
   ```

2. **Deployment Testing**:
   ```bash
   # Deploy with DABS
   databricks bundle deploy
   databricks bundle run o11y_jmr_app
   
   # Monitor logs
   python dba_logz.py <app-url> --search "Lakebase"
   
   # Test deployed endpoints
   python dba_client.py <app-url> /api/services/list
   ```

### Phase 4: Production Cutover
1. Deploy to production with `DATA_BACKEND=lakebase`
2. Monitor performance metrics
3. Validate query results match SQL Warehouse
4. Rollback plan: Set `DATA_BACKEND=warehouse`

## SQL Syntax Differences

### Spark SQL → PostgreSQL Conversions

| Spark SQL | PostgreSQL | Notes |
|-----------|------------|-------|
| `LATERAL VIEW explode(arr) AS x` | `CROSS JOIN LATERAL unnest(arr) AS x(x)` | Array expansion |
| `INTERVAL 1 HOUR` | `INTERVAL '1 hour'` | Quoted intervals |
| `array_contains(arr, 'val')` | `'val' = ANY(arr)` | Array membership |
| `PERCENTILE_CONT(0.5) WITHIN GROUP` | Same | Compatible syntax |
| `NOW()` | `CURRENT_TIMESTAMP` or `NOW()` | Both work |
| `date_trunc('minute', ts)` | Same | Compatible |

### Table Name Mappings

| Unity Catalog | Lakebase Synced |
|---------------|-----------------|
| `traces_assembled_silver` | `traces_assembled_synced` |
| `traces_silver` | `traces_silver_synced` |
| `service_dependencies` | `service_dependencies_synced` |
| `metrics_1min` | `metrics_1min_synced` |
| `logs` | `logs_synced` |

## Performance Expectations

### Expected Improvements
- **Lower latency**: PostgreSQL optimized for OLTP workloads
- **Better concurrency**: Connection pooling with OAuth token refresh
- **Reduced cost**: No warehouse compute costs per query

### Monitoring
- Track query execution times in application logs
- Monitor Lakebase instance metrics in Databricks console
- Compare P50/P95/P99 latencies before/after migration

## Troubleshooting

### Common Issues

**1. OAuth Token Expiration**
- Symptom: Authentication errors after 15 minutes
- Solution: LakebaseManager automatically refreshes tokens
- Check: Logs should show "Refreshing PostgreSQL OAuth token"

**2. SQL Syntax Errors**
- Symptom: Query execution fails with PostgreSQL syntax errors
- Solution: Update `sql_converter.py` with new conversion rules
- Debug: Check converted query in logs

**3. Connection Pool Exhaustion**
- Symptom: "No connections available" errors
- Solution: Increase `pool_size` or `max_overflow` in LakebaseManager
- Default: 5 connections, 10 overflow

**4. Missing Environment Variables**
- Symptom: "LAKEBASE_HOST environment variable is required"
- Solution: Ensure all Lakebase env vars set in app.yml
- Check: `LAKEBASE_HOST`, `LAKEBASE_INSTANCE_NAME`

## Rollback Procedure

If issues arise, rollback to SQL Warehouse:

1. **Update app.yml**:
   ```yaml
   env:
     - name: DATA_BACKEND
       value: warehouse  # Change from lakebase
   ```

2. **Redeploy**:
   ```bash
   databricks bundle deploy
   databricks bundle run o11y_jmr_app
   ```

3. **Verify**:
   - Check logs for "Using SQL Warehouse backend"
   - Test endpoints return expected data

## Next Steps

1. **Complete Router Migration**:
   - Apply pattern from `services_lakebase_example.py` to all routers
   - Test each endpoint individually

2. **Performance Validation**:
   - Run load tests comparing warehouse vs lakebase
   - Measure P50/P95/P99 latencies
   - Document performance improvements

3. **Production Deployment**:
   - Deploy to dev environment first
   - Validate for 24 hours
   - Deploy to production with monitoring

4. **Cleanup**:
   - Remove SQL Warehouse fallback after stable period
   - Update documentation
   - Archive old warehouse queries

## References

- [Databricks Lakebase Documentation](https://docs.databricks.com/en/oltp/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Array Functions](https://www.postgresql.org/docs/current/functions-array.html)
- [Databricks OAuth Token Generation](https://docs.databricks.com/en/dev-tools/auth.html)
