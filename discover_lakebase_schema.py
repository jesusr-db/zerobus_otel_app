#!/usr/bin/env python3
"""Discover actual table names and schema in Lakebase instance."""

from databricks.sdk import WorkspaceClient
from sqlalchemy import create_engine, text
import uuid
import time

def discover_lakebase_schema():
    """Connect to Lakebase and list available tables."""
    w = WorkspaceClient()
    
    # Lakebase configuration
    instance_name = "zerobus-dev"
    database_name = "databricks_postgres"
    host = "instance-6125d6d9-44a4-46b7-a5ff-6db65cbf60c5.database.cloud.databricks.com"
    port = 5432
    sp_id = "2b35926f-40c4-4c46-a2d0-bb5981beed09"
    
    print(f"🔍 Discovering Lakebase schema...")
    print(f"   Instance: {instance_name}")
    print(f"   Database: {database_name}")
    print(f"   Host: {host}")
    print()
    
    # Generate OAuth token
    print("🔑 Generating OAuth token...")
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[instance_name]
    )
    token = cred.token
    print("✅ Token generated")
    print()
    
    # Create connection
    connection_string = f"postgresql+psycopg2://{sp_id}:{token}@{host}:{port}/{database_name}?sslmode=require"
    engine = create_engine(connection_string, echo=False)
    
    try:
        with engine.connect() as conn:
            # List all schemas
            print("📂 Available Schemas:")
            print("-" * 80)
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name
            """))
            schemas = [row[0] for row in result]
            for schema in schemas:
                print(f"  • {schema}")
            print()
            
            # For each schema, list tables
            for schema in schemas:
                print(f"📊 Tables in schema '{schema}':")
                print("-" * 80)
                result = conn.execute(text(f"""
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = '{schema}'
                    ORDER BY table_name
                """))
                tables = list(result)
                if tables:
                    for table_name, table_type in tables:
                        print(f"  • {schema}.{table_name} ({table_type})")
                else:
                    print(f"  (no tables found)")
                print()
            
            # Look specifically for observability-related tables
            print("🔍 Searching for observability tables (traces, logs, metrics, spans):")
            print("-" * 80)
            result = conn.execute(text("""
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
            obs_tables = list(result)
            if obs_tables:
                for schema, table_name, table_type in obs_tables:
                    print(f"  • {schema}.{table_name} ({table_type})")
            else:
                print("  ❌ No observability tables found!")
            print()
            
            # Sample one table if exists
            if obs_tables:
                schema, table_name, _ = obs_tables[0]
                print(f"📋 Sample structure of {schema}.{table_name}:")
                print("-" * 80)
                result = conn.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = '{schema}'
                      AND table_name = '{table_name}'
                    ORDER BY ordinal_position
                    LIMIT 20
                """))
                for col_name, data_type, nullable in result:
                    null_str = "NULL" if nullable == "YES" else "NOT NULL"
                    print(f"  • {col_name}: {data_type} {null_str}")
                print()
            
            print("✅ Schema discovery complete!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    discover_lakebase_schema()
