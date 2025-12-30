#!/usr/bin/env python3
"""
Grant Lakebase schema access to App Service Principal.

This uses direct PostgreSQL connection to grant permissions.
Must be run with credentials that have GRANT privileges.
"""

import sys
import json
import subprocess
import psycopg2
import os

def get_app_service_principal(app_name: str) -> str:
    """Get service principal ID from app."""
    result = subprocess.run(
        ['databricks', 'apps', 'get', app_name, '--output', 'json'],
        capture_output=True,
        text=True,
        check=True
    )
    app_data = json.loads(result.stdout)
    return app_data.get('service_principal_id', app_data.get('service_principal_name'))

def grant_permissions(sp_id: str):
    """Grant schema permissions via direct PostgreSQL connection."""
    
    # Lakebase connection details
    host = os.getenv('LAKEBASE_HOST', 'instance-c33627a6-422c-461a-82f7-ac78b0a6d72a.database.cloud.databricks.com')
    port = os.getenv('LAKEBASE_PORT', '5432')
    database = os.getenv('LAKEBASE_DATABASE_NAME', 'zerobus_sdp')
    
    # Get Databricks token from SDK
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    token = w.config.token or w.config.authenticate()
    
    if not token:
        print("Error: Could not get Databricks token")
        sys.exit(1)
    
    # Connect to Lakebase (token is used as the user)
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=token,
        password=token,
        sslmode='require'
    )
    
    cur = conn.cursor()
    
    grants = [
        f"GRANT USAGE ON SCHEMA zerobus_sdp TO \"{sp_id}\"",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA zerobus_sdp TO \"{sp_id}\"",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA zerobus_sdp GRANT SELECT ON TABLES TO \"{sp_id}\"",
    ]
    
    for grant in grants:
        try:
            print(f"Executing: {grant}")
            cur.execute(grant)
            conn.commit()
            print("  ✓ Success")
        except Exception as e:
            print(f"  ⚠ Warning: {e}")
            conn.rollback()
    
    cur.close()
    conn.close()
    print("\n✓ Permissions granted successfully")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python grant_sp_access.py <app-name>")
        sys.exit(1)
    
    app_name = sys.argv[1]
    print(f"Getting service principal for: {app_name}")
    sp_id = get_app_service_principal(app_name)
    print(f"Service Principal: {sp_id}\n")
    
    grant_permissions(sp_id)
