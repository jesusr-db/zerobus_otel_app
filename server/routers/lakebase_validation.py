"""
Lakebase Validation Endpoints

Test endpoints for validating Lakebase migration.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
import logging

from server.services.lakebase_validator import LakebaseValidator, validate_lakebase_setup
from server.config import OBSERVABILITY_TABLE_PREFIX

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lakebase-validation", tags=["validation"])


@router.get("/connectivity")
async def test_connectivity(request: Request, discover: bool = Query(default=False, description="Include schema discovery")):
    """
    Test connectivity to both SQL Warehouse and Lakebase.
    
    Returns connection status and configuration details.
    Add ?discover=true to include schema discovery.
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")
    
    try:
        results = validate_lakebase_setup(user_token=user_token)
        
        if not results["overall_status"]:
            raise HTTPException(
                status_code=500,
                detail="Connectivity test failed - check logs for details"
            )
        
        # Add schema discovery if requested
        if discover:
            try:
                from server.services.lakebase_manager import LakebaseManager
                from sqlalchemy import text
                
                lakebase = LakebaseManager(user_token=user_token)
                
                engine = lakebase._get_engine()
                with engine.connect() as conn:
                    schema_info = {
                        "schemas": [],
                        "tables": {},
                        "observability_tables": []
                    }
                    
                    # Get schemas
                    schemas_result = conn.execute(text("""
                        SELECT schema_name 
                        FROM information_schema.schemata 
                        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                        ORDER BY schema_name
                    """))
                    schemas = [row[0] for row in schemas_result]
                    schema_info["schemas"] = schemas
                    
                    # Get tables for each schema
                    for schema in schemas:
                        tables_result = conn.execute(text(f"""
                            SELECT table_name, table_type
                            FROM information_schema.tables
                            WHERE table_schema = '{schema}'
                            ORDER BY table_name
                        """))
                        tables = [(row[0], row[1]) for row in tables_result]
                        schema_info["tables"][schema] = [
                            {"name": name, "type": type_} for name, type_ in tables
                        ]
                    
                    # Get observability tables
                    obs_result = conn.execute(text("""
                        SELECT table_schema, table_name, table_type
                        FROM information_schema.tables
                        WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                          AND (
                              table_name LIKE '%trace%'
                              OR table_name LIKE '%log%'
                              OR table_name LIKE '%metric%'
                              OR table_name LIKE '%span%'
                              OR table_name LIKE '%service%'
                              OR table_name LIKE '%otel%'
                          )
                        ORDER BY table_schema, table_name
                    """))
                    obs_tables = [(row[0], row[1], row[2]) for row in obs_result]
                    schema_info["observability_tables"] = [
                        {"schema": schema, "name": name, "type": type_}
                        for schema, name, type_ in obs_tables
                    ]
                    
                    results["schema_discovery"] = schema_info
                    
            except Exception as e:
                logger.error(f"Schema discovery failed: {e}", exc_info=True)
                results["schema_discovery"] = {"error": str(e)}
        
        return results
    except Exception as e:
        logger.error(f"Connectivity test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-query")
async def validate_query_conversion(
    request: Request,
    endpoint_name: str = Query(..., description="Name of endpoint being tested"),
    spark_query: str = Query(..., description="Spark SQL query to validate")
):
    """
    Validate Spark SQL to PostgreSQL conversion.
    
    Shows original query, converted query, and detected changes.
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")
    validator = LakebaseValidator(user_token=user_token)
    
    try:
        results = validator.validate_query_conversion(spark_query, endpoint_name)
        return results
    except Exception as e:
        logger.error(f"Query validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-results")
async def compare_query_results(
    request: Request,
    endpoint_name: str = Query(..., description="Name of endpoint being tested"),
    spark_query: str = Query(..., description="Spark SQL query to compare"),
    sample_limit: int = Query(default=5, description="Number of sample rows to return")
):
    """
    Execute query on both backends and compare results.
    
    Returns row counts, sample data, and differences if any.
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")
    validator = LakebaseValidator(user_token=user_token)
    
    try:
        results = validator.compare_results(spark_query, endpoint_name, sample_limit)
        
        if not results["warehouse"]["success"] or not results["lakebase"]["success"]:
            raise HTTPException(
                status_code=500,
                detail="Query execution failed on one or both backends"
            )
        
        if not results["match"]:
            logger.warning(f"Results mismatch for {endpoint_name}")
        
        return results
    except Exception as e:
        logger.error(f"Result comparison failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-simple-query")
async def test_simple_query(request: Request):
    """Test simple SELECT * to understand schema."""
    user_token = request.headers.get("X-Forwarded-Access-Token")
    
    try:
        from server.services.lakebase_manager import LakebaseManager
        from sqlalchemy import text
        
        lakebase = LakebaseManager(user_token=user_token)
        engine = lakebase._get_engine()
        
        with engine.connect() as conn:
            # Get table structure
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'zerobus_sdp' 
                  AND table_name = 'traces_assembled_synced'
                ORDER BY ordinal_position
            """))
            columns = [{"name": row[0], "type": row[1]} for row in result]
            
            # Get sample data
            result = conn.execute(text("""
                SELECT * 
                FROM zerobus_sdp.traces_assembled_synced 
                LIMIT 1
            """))
            sample_row = None
            for row in result:
                sample_row = dict(row._mapping)
                # Convert JSONB to string for display
                if 'span_details' in sample_row and sample_row['span_details']:
                    # span_details is already a list/dict from PostgreSQL JSONB
                    if isinstance(sample_row['span_details'], list):
                        sample_row['span_details'] = sample_row['span_details'][:2]
                    elif isinstance(sample_row['span_details'], str):
                        import json
                        sample_row['span_details'] = json.loads(sample_row['span_details'])[:2]
                break
            
            return {
                "columns": columns,
                "sample_row": sample_row
            }
            
    except Exception as e:
        logger.error(f"Simple query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-services-query-native")
async def test_services_query_native(
    request: Request,
    time_range: str = Query(default="90 days", description="Time range like '1 hour', '24 hours', '90 days'")
):
    """
    Test services query with native PostgreSQL (no conversion).
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")
    
    try:
        from server.services.lakebase_manager import LakebaseManager
        from sqlalchemy import text
        
        lakebase = LakebaseManager(user_token=user_token)
        engine = lakebase._get_engine()
        
        # Native PostgreSQL query for Lakebase
        lakebase_query = f"""
        WITH current_spans AS (
          SELECT 
            span_value->>'service_name' as service_name,
            (span_value->>'duration_ms')::float as duration_ms
          FROM zerobus_sdp.traces_assembled_synced t
          CROSS JOIN LATERAL jsonb_array_elements(t.span_details) AS span_value
          WHERE t.trace_start >= NOW() - INTERVAL '{time_range}'
        )
        SELECT 
          service_name,
          COUNT(*) as request_count,
          AVG(duration_ms) as avg_duration
        FROM current_spans
        GROUP BY service_name
        ORDER BY request_count DESC
        LIMIT 10
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(lakebase_query))
            rows = [dict(row._mapping) for row in result]
            
            return {
                "success": True,
                "row_count": len(rows),
                "results": rows,
                "query": lakebase_query
            }
            
    except Exception as e:
        logger.error(f"Native query failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "query": lakebase_query if 'lakebase_query' in locals() else None
        }


@router.get("/test-services-query")
async def test_services_query(
    request: Request,
    time_range: str = Query(default="1h", description="Time range: 1h or 24h")
):
    """
    Test the services list query on both backends.
    
    This is a convenience endpoint that validates the main services query.
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")
    validator = LakebaseValidator(user_token=user_token)
    
    # Get time range interval
    intervals = {"1h": "1 hour", "24h": "24 hour"}
    interval = intervals.get(time_range, "1 hour")
    seconds = 3600 if time_range == "1h" else 86400
    
    # Build the services query
    spark_query = f"""
    WITH current_spans AS (
      SELECT 
        span.service_name,
        span.duration_ms,
        span.is_error,
        t.trace_start
      FROM {OBSERVABILITY_TABLE_PREFIX}.traces_assembled_silver t
      LATERAL VIEW explode(span_details) AS span
      WHERE t.trace_start >= NOW() - INTERVAL {interval}
    ),
    current_metrics AS (
      SELECT
        service_name,
        COUNT(*) as request_count,
        AVG(duration_ms) as avg_duration
      FROM current_spans
      GROUP BY service_name
    )
    SELECT 
      service_name,
      request_count,
      avg_duration
    FROM current_metrics
    ORDER BY request_count DESC
    LIMIT 10
    """
    
    try:
        results = validator.compare_results(
            spark_query=spark_query,
            endpoint_name=f"services-list-{time_range}",
            limit=3
        )
        
        return {
            "test": "services-list",
            "time_range": time_range,
            "results": results
        }
    except Exception as e:
        logger.error(f"Services query test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover-schema")
async def discover_lakebase_schema(request: Request):
    """
    Discover actual table names and schema in Lakebase instance.
    
    Queries information_schema to list:
    - All available schemas
    - Tables in each schema
    - Observability-related tables (traces, logs, metrics, spans)
    - Sample column structure of found tables
    """
    user_token = request.headers.get("X-Forwarded-Access-Token")
    
    logger.info("=" * 80)
    logger.info("Schema Discovery Request Started")
    logger.info(f"User token present: {bool(user_token)}")
    logger.info("=" * 80)
    
    try:
        from server.services.lakebase_manager import LakebaseManager
        from sqlalchemy import text
        
        logger.info("Creating LakebaseManager...")
        lakebase = LakebaseManager(user_token=user_token)
        logger.info(f"LakebaseManager created: instance={lakebase.instance_name}, db={lakebase.database_name}")
        
        logger.info("Getting database connection...")
        engine = lakebase._get_engine()
        with engine.connect() as conn:
            logger.info("Connection established, starting queries...")
            result = {
                "instance": {
                    "name": lakebase.instance_name,
                    "database": lakebase.database_name,
                    "catalog": lakebase.catalog_name,
                    "schema": lakebase.schema_name,
                    "host": lakebase.db_host,
                    "port": lakebase.db_port
                },
                "schemas": [],
                "tables": {},
                "observability_tables": [],
                "sample_structures": {}
            }
            
            # Get current database
            current_db = conn.execute(text("SELECT current_database()")).scalar()
            logger.info(f"Current database: {current_db}")
            result["current_database"] = current_db
            
            # Get all schemas (including checking for zerobus_sdp specifically)
            schemas_result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                ORDER BY schema_name
            """))
            all_schemas = [row[0] for row in schemas_result]
            logger.info(f"All schemas in database: {all_schemas}")
            
            # Filter out system schemas
            schemas = [s for s in all_schemas if s not in ('pg_catalog', 'information_schema', 'pg_toast')]
            logger.info(f"User schemas: {schemas}")
            result["schemas"] = schemas
            result["all_schemas_raw"] = all_schemas
            
            for schema in schemas:
                tables_result = conn.execute(text(f"""
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = '{schema}'
                    ORDER BY table_name
                """))
                tables = [(row[0], row[1]) for row in tables_result]
                result["tables"][schema] = [
                    {"name": name, "type": type_} for name, type_ in tables
                ]
            
            obs_result = conn.execute(text("""
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                  AND (
                      table_name LIKE '%trace%'
                      OR table_name LIKE '%log%'
                      OR table_name LIKE '%metric%'
                      OR table_name LIKE '%span%'
                      OR table_name LIKE '%service%'
                      OR table_name LIKE '%otel%'
                  )
                ORDER BY table_schema, table_name
            """))
            obs_tables = [(row[0], row[1], row[2]) for row in obs_result]
            result["observability_tables"] = [
                {"schema": schema, "name": name, "type": type_}
                for schema, name, type_ in obs_tables
            ]
            
            if obs_tables:
                schema, table_name, _ = obs_tables[0]
                columns_result = conn.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = '{schema}'
                      AND table_name = '{table_name}'
                    ORDER BY ordinal_position
                    LIMIT 20
                """))
                columns = [
                    {
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == "YES"
                    }
                    for row in columns_result
                ]
                result["sample_structures"][f"{schema}.{table_name}"] = columns
            
            return result
            
    except Exception as e:
        logger.error(f"Schema discovery failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def validation_health():
    """Health check for validation endpoints."""
    return {
        "status": "healthy",
        "endpoints": [
            "/lakebase-validation/connectivity",
            "/lakebase-validation/validate-query",
            "/lakebase-validation/compare-results",
            "/lakebase-validation/test-services-query",
            "/lakebase-validation/discover-schema"
        ]
    }
