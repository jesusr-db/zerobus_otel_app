# Lakebase SQL Conversion Guide

**Purpose**: Reference guide for converting Spark SQL (SQL Warehouse) queries to PostgreSQL (Lakebase) queries.

**Date**: 2026-01-21
**Status**: Active Migration Guide

---

## Table Name Conversions

| Spark SQL (Warehouse) | PostgreSQL (Lakebase) | Notes |
|----------------------|----------------------|-------|
| `jmr_demo.zerobus_sdp.traces_assembled_silver` | `zerobus_sdp.traces_assembled_synced` | Remove catalog prefix |
| `jmr_demo.zerobus_sdp.traces_silver` | `zerobus_sdp.traces_silver_synced` | Add `_synced` suffix |
| `jmr_demo.zerobus_sdp.logs_raw_silver` | `zerobus_sdp.logs_synced` | Simplified name |
| `jmr_demo.zerobus_sdp.metrics_raw_silver` | `zerobus_sdp.metrics_1min_synced` | Granularity specified |
| `jmr_demo.zerobus_sdp.service_dependencies` | `zerobus_sdp.service_dependencies_synced` | Add `_synced` suffix |

**Pattern**: Remove `{catalog}.` prefix, use `_synced` suffix, schema remains `zerobus_sdp`

---

## Array/JSONB Explosion Conversion

### Spark SQL Pattern (Warehouse)
```sql
SELECT
  span.service_name,
  span.duration_ms,
  span.is_error
FROM {OBSERVABILITY_TABLE_PREFIX}.traces_assembled_silver t
LATERAL VIEW explode(span_details) AS span
WHERE t.trace_start >= NOW() - INTERVAL 1 HOUR
```

### PostgreSQL Pattern (Lakebase)
```sql
SELECT
  span_value->>'service_name' as service_name,
  (span_value->>'duration_ms')::float as duration_ms,
  (span_value->>'is_error')::boolean as is_error
FROM {LAKEBASE_SCHEMA_NAME}.traces_assembled_synced t
CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
WHERE t.trace_start >= NOW() - INTERVAL '1 hour'
```

**Key Changes:**
1. `LATERAL VIEW explode(span_details) AS span` → `CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value`
2. `span.field_name` → `span_value->>'field_name'`
3. Numeric fields need type casting: `(span_value->>'duration_ms')::float`
4. Boolean fields need type casting: `(span_value->>'is_error')::boolean`

---

## Field Access Conversion

| Spark SQL | PostgreSQL | Type | Notes |
|-----------|------------|------|-------|
| `span.service_name` | `span_value->>'service_name'` | text | Direct text extraction |
| `span.duration_ms` | `(span_value->>'duration_ms')::float` | float | Must cast numeric |
| `span.is_error` | `(span_value->>'is_error')::boolean` | boolean | Must cast boolean |
| `span.span_id` | `span_value->>'span_id'` | text | Direct text extraction |
| `span.parent_span_id` | `span_value->>'parent_span_id'` | text | Direct text extraction |
| `span.name` | `span_value->>'name'` | text | Direct text extraction |
| `span.kind` | `span_value->>'kind'` | text | Direct text extraction |
| `span.start_offset_ms` | `(span_value->>'start_offset_ms')::float` | float | Must cast numeric |

**Operator Reference:**
- `->` : Extract JSON object as JSON
- `->>` : Extract JSON object as text
- `::type` : Cast to PostgreSQL type

---

## Interval Syntax Conversion

| Spark SQL | PostgreSQL | Example |
|-----------|------------|---------|
| `INTERVAL 1 HOUR` | `INTERVAL '1 hour'` | Time intervals need quotes |
| `INTERVAL 5 MINUTE` | `INTERVAL '5 minutes'` | Use plural form |
| `INTERVAL 1 DAY` | `INTERVAL '1 day'` | Singular vs context |
| `INTERVAL 7 DAY` | `INTERVAL '7 days'` | Use plural for multiple |
| `INTERVAL {interval}` | `INTERVAL '{interval}'` | Variable intervals quoted |

**Rule**: Always quote intervals in PostgreSQL, use lowercase, prefer plural forms for quantities > 1

---

## Array Functions Conversion

### array_contains()

**Spark SQL:**
```sql
WHERE array_contains(services_involved, 'frontend')
```

**PostgreSQL:**
```sql
WHERE services_involved::jsonb @> '"frontend"'::jsonb
OR services_involved::jsonb @> '["frontend"]'::jsonb
```

**Alternative (safer):**
```sql
WHERE EXISTS (
  SELECT 1 FROM jsonb_array_elements_text(services_involved) AS service
  WHERE service = 'frontend'
)
```

---

## Aggregation Functions

Most aggregation functions are compatible between Spark SQL and PostgreSQL:

| Function | Spark SQL | PostgreSQL | Notes |
|----------|-----------|------------|-------|
| `COUNT(*)` | ✓ | ✓ | Compatible |
| `AVG(field)` | ✓ | ✓ | Compatible |
| `SUM(field)` | ✓ | ✓ | Compatible |
| `MAX(field)` | ✓ | ✓ | Compatible |
| `MIN(field)` | ✓ | ✓ | Compatible |
| `PERCENTILE_CONT` | ✓ | ✓ | Compatible syntax |

**PERCENTILE_CONT Example (identical syntax):**
```sql
PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95
```

---

## Date/Time Functions

| Spark SQL | PostgreSQL | Notes |
|-----------|------------|-------|
| `NOW()` | `NOW()` | Compatible |
| `date_trunc('hour', field)` | `date_trunc('hour', field)` | Compatible |
| `date_trunc('MINUTE', field)` | `date_trunc('minute', field)` | Use lowercase |

---

## Complete Conversion Example

### Before: Spark SQL Service Metrics Query
```sql
WITH service_spans AS (
  SELECT
    span.duration_ms,
    span.is_error,
    t.trace_start
  FROM jmr_demo.zerobus_sdp.traces_assembled_silver t
  LATERAL VIEW explode(span_details) AS span
  WHERE span.service_name = 'frontend'
    AND t.trace_start >= NOW() - INTERVAL 1 HOUR
)
SELECT
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
  AVG(duration_ms) as avg_duration_ms,
  SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
  COUNT(*) as request_count
FROM service_spans
```

### After: PostgreSQL Service Metrics Query
```sql
WITH service_spans AS (
  SELECT
    (span_value->>'duration_ms')::float as duration_ms,
    (span_value->>'is_error')::boolean as is_error,
    t.trace_start
  FROM zerobus_sdp.traces_assembled_synced t
  CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
  WHERE span_value->>'service_name' = 'frontend'
    AND t.trace_start >= NOW() - INTERVAL '1 hour'
)
SELECT
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as latency_p95,
  AVG(duration_ms) as avg_duration_ms,
  SUM(CASE WHEN is_error THEN 1 ELSE 0 END) as error_count,
  COUNT(*) as request_count
FROM service_spans
```

**Changes Applied:**
1. ✅ Table: `jmr_demo.zerobus_sdp.traces_assembled_silver` → `zerobus_sdp.traces_assembled_synced`
2. ✅ Explosion: `LATERAL VIEW explode(span_details) AS span` → `CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value`
3. ✅ Field access: `span.duration_ms` → `(span_value->>'duration_ms')::float`
4. ✅ Field access: `span.is_error` → `(span_value->>'is_error')::boolean`
5. ✅ Field access: `span.service_name` → `span_value->>'service_name'`
6. ✅ Interval: `INTERVAL 1 HOUR` → `INTERVAL '1 hour'`

---

## Common Gotchas

### 1. Missing Type Casts
❌ **Wrong:**
```sql
WHERE (span_value->>'duration_ms') > 100  -- Compares as text, not number!
```

✅ **Correct:**
```sql
WHERE (span_value->>'duration_ms')::float > 100
```

### 2. Interval Without Quotes
❌ **Wrong:**
```sql
WHERE trace_start >= NOW() - INTERVAL 1 hour
```

✅ **Correct:**
```sql
WHERE trace_start >= NOW() - INTERVAL '1 hour'
```

### 3. Catalog Prefix in Table Names
❌ **Wrong:**
```sql
FROM jmr_demo.zerobus_sdp.traces_assembled_synced
```

✅ **Correct:**
```sql
FROM zerobus_sdp.traces_assembled_synced
```

### 4. Wrong Array Element Alias
❌ **Wrong:**
```sql
LATERAL VIEW explode(span_details) AS span  -- Spark SQL syntax
WHERE span.service_name = 'frontend'
```

✅ **Correct:**
```sql
CROSS JOIN LATERAL jsonb_array_elements(span_details) AS span_value
WHERE span_value->>'service_name' = 'frontend'
```

---

## Validation Checklist

After converting a query, verify:

- [ ] All table names updated (no catalog prefix, `_synced` suffix)
- [ ] All `LATERAL VIEW explode()` replaced with `CROSS JOIN LATERAL jsonb_array_elements()`
- [ ] All field accesses use `->>`operator
- [ ] All numeric fields have `::float` or `::int` cast
- [ ] All boolean fields have `::boolean` cast
- [ ] All intervals have quotes: `INTERVAL '1 hour'`
- [ ] No `array_contains()` - use JSONB operators instead
- [ ] Variable substitution uses correct table prefix variable
- [ ] Query tested against actual Lakebase data

---

## Testing Strategy

1. **Syntax Validation**: Run query directly in PostgreSQL client (psql, DBeaver)
2. **Data Validation**: Compare results with warehouse query output
3. **Performance Validation**: Ensure query executes in < 2 seconds
4. **Edge Case Testing**: Test with empty results, null values, missing fields

---

## References

- **Lakebase Migration Doc**: `docs/LAKEBASE_MIGRATION_COMPLETE.md`
- **PostgreSQL JSONB Functions**: https://www.postgresql.org/docs/current/functions-json.html
- **SQL Converter Utility**: `server/services/sql_converter.py` (use with caution)
- **Validation Endpoints**: `server/routers/lakebase_validation.py`

---

## Conversion Tracking

### Endpoints Already Migrated
- ✅ `/api/services/list` - services.py:49 (has both versions)
- ✅ `/api/traces` - traces.py:37 (has both versions)
- ✅ `/api/traces/waterfall/{id}` - traces.py:125 (has both versions)
- ✅ `/api/dependencies/graph` - dependencies.py:37 (has both versions)

### Endpoints Pending Migration
- ❌ `/api/services/{service}/metrics` - services.py:230 (hardcoded warehouse)
- ❌ `/api/services/{service}/dependencies` - services.py:338 (hardcoded warehouse)
- ❌ `/api/services/{service}/traces` - services.py:468 (hardcoded warehouse)
- ❌ `/api/services/{service}/traces/{id}` - services.py:506 (hardcoded warehouse)

**Target**: Convert all ❌ endpoints to Lakebase, remove DATA_BACKEND conditionals
