#!/usr/bin/env python3
"""
Grant Lakebase permissions to the deployed app's service principal.

This script:
1. Gets the service principal ID from the deployed app
2. Connects to Lakebase using admin credentials
3. Grants necessary permissions on database, schema, and tables
"""

import os
import sys
import json
import subprocess
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import psycopg2
import uuid


def get_app_service_principal(app_name: str) -> dict:
    """Get service principal info from deployed app."""
    print(f"Getting service principal for app: {app_name}")
    
    result = subprocess.run(
        ['databricks', 'apps', 'get', app_name, '--output', 'json'],
        capture_output=True,
        text=True,
        check=True
    )
    
    app_data = json.loads(result.stdout)
    sp_info = {
        'client_id': app_data.get('service_principal_client_id'),
        'sp_id': app_data.get('service_principal_id'),
        'name': app_data.get('service_principal_name')
    }
    
    print(f"  Client ID: {sp_info['client_id']}")
    print(f"  SP ID: {sp_info['sp_id']}")
    print(f"  Name: {sp_info['name']}")
    
    return sp_info


def get_lakebase_token(instance_name: str) -> str:
    """Generate OAuth token for Lakebase connection."""
    print(f"\nGenerating Lakebase token for instance: {instance_name}")
    
    # Use workspace client with default auth
    w = WorkspaceClient()
    
    # Generate database credential
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[instance_name]
    )
    
    print("  Token generated successfully")
    return cred.token


def grant_permissions(sp_client_id: str, lakebase_config: dict):
    """Grant Lakebase permissions to service principal."""
    print(f"\nConnecting to Lakebase...")
    print(f"  Host: {lakebase_config['host']}")
    print(f"  Database: {lakebase_config['database']}")
    print(f"  Schema: {lakebase_config['schema']}")
    
    # Get admin token for connection
    token = get_lakebase_token(lakebase_config['instance_name'])
    
    # Connect to Lakebase
    conn = psycopg2.connect(
        host=lakebase_config['host'],
        port=lakebase_config['port'],
        database=lakebase_config['database'],
        user=token,  # Token is used as username
        password=token,  # Token is also password
        sslmode='require'
    )
    
    cur = conn.cursor()
    schema = lakebase_config['schema']
    database = lakebase_config['database']
    
    grants = [
        f'GRANT CONNECT ON DATABASE {database} TO "{sp_client_id}"',
        f'GRANT USAGE ON SCHEMA {schema} TO "{sp_client_id}"',
        f'GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO "{sp_client_id}"',
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT SELECT ON TABLES TO "{sp_client_id}"',
    ]
    
    print(f"\nGranting permissions to service principal: {sp_client_id}")
    
    for grant in grants:
        try:
            print(f"  Executing: {grant}")
            cur.execute(grant)
            conn.commit()
            print("    ✓ Success")
        except Exception as e:
            print(f"    ⚠ Warning: {e}")
            conn.rollback()
            # Continue with other grants even if one fails
    
    cur.close()
    conn.close()
    print("\n✓ Permissions granted successfully")


def main():
    """Main execution."""
    # Configuration
    app_name = os.getenv('APP_NAME', 'o11y-jmr')
    
    lakebase_config = {
        'instance_name': os.getenv('LAKEBASE_INSTANCE_NAME', 'zerobus-dev'),
        'host': os.getenv('LAKEBASE_HOST', 'instance-c33627a6-422c-461a-82f7-ac78b0a6d72a.database.cloud.databricks.com'),
        'port': int(os.getenv('LAKEBASE_PORT', '5432')),
        'database': os.getenv('LAKEBASE_DATABASE_NAME', 'zerobus_sdp'),
        'schema': os.getenv('LAKEBASE_SCHEMA_NAME', 'zerobus_sdp'),
    }
    
    try:
        # Get app service principal
        sp_info = get_app_service_principal(app_name)
        
        if not sp_info['client_id']:
            print("ERROR: Could not get service principal client ID from app")
            sys.exit(1)
        
        # Grant permissions
        grant_permissions(sp_info['client_id'], lakebase_config)
        
        print("\n" + "="*60)
        print("SUCCESS: Lakebase permissions granted")
        print("="*60)
        print(f"App: {app_name}")
        print(f"Service Principal: {sp_info['client_id']}")
        print(f"Database: {lakebase_config['database']}")
        print(f"Schema: {lakebase_config['schema']}")
        print("="*60)
        
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Failed to get app info: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
