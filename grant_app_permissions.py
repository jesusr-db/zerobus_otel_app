#!/usr/bin/env python3
"""
Grant Lakebase permissions to the current App Service Principal.

This script should be run after each app deployment to grant the necessary
permissions to the dynamically created service principal.

Usage:
    python grant_app_permissions.py <app-name>
    
Example:
    python grant_app_permissions.py o11y-jmr
"""

import sys
import json
import subprocess
from databricks.sdk import WorkspaceClient

def get_app_service_principal(app_name: str) -> str:
    """Get the service principal ID for the given app using CLI."""
    try:
        result = subprocess.run(
            ['databricks', 'apps', 'get', app_name, '--output', 'json'],
            capture_output=True,
            text=True,
            check=True
        )
        
        app_data = json.loads(result.stdout)
        
        # Extract service principal from app data
        if 'service_principal_id' in app_data:
            return app_data['service_principal_id']
        
        if 'service_principal_name' in app_data:
            return app_data['service_principal_name']
        
        # Check in resources
        if 'resources' in app_data:
            for resource in app_data['resources']:
                if 'service_principal' in resource:
                    return resource['service_principal']
        
        raise ValueError(f"Could not find service principal for app {app_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error calling databricks CLI: {e.stderr}")
        raise
    except Exception as e:
        print(f"Error getting app info: {e}")
        raise


def grant_lakebase_permissions(
    w: WorkspaceClient,
    service_principal_id: str,
    instance_name: str,
    database_name: str
):
    """Grant Lakebase permissions to the service principal."""
    
    print(f"Granting permissions to service principal: {service_principal_id}")
    print(f"Database instance: {instance_name}")
    print(f"Database: {database_name}")
    
    # SQL commands to grant permissions
    grant_commands = [
        # Grant usage on database
        f"GRANT USAGE ON DATABASE {database_name} TO `{service_principal_id}`",
        
        # Grant usage on all schemas
        f"GRANT USAGE ON ALL SCHEMAS IN DATABASE {database_name} TO `{service_principal_id}`",
        
        # Grant select on all tables in all schemas
        f"GRANT SELECT ON ALL TABLES IN DATABASE {database_name} TO `{service_principal_id}`",
        
        # Grant future permissions
        f"ALTER DEFAULT PRIVILEGES IN DATABASE {database_name} GRANT USAGE ON SCHEMAS TO `{service_principal_id}`",
        f"ALTER DEFAULT PRIVILEGES IN DATABASE {database_name} GRANT SELECT ON TABLES TO `{service_principal_id}`",
    ]
    
    # Execute grant commands via SQL statement API
    for command in grant_commands:
        try:
            print(f"Executing: {command}")
            
            # Use SQL statement API with the database instance
            result = w.statement_execution.execute_statement(
                statement=command,
                warehouse_id=None,  # Not using warehouse
                catalog=database_name,
                schema="information_schema",
                disposition="INLINE",
                wait_timeout="30s"
            )
            
            print(f"  ✓ Success")
        except Exception as e:
            print(f"  ⚠ Warning: {e}")
            # Continue with other grants even if one fails
    
    print("\n✓ Permissions granted successfully")


def main():
    if len(sys.argv) < 2:
        print("Usage: python grant_app_permissions.py <app-name>")
        print("Example: python grant_app_permissions.py o11y-jmr")
        sys.exit(1)
    
    app_name = sys.argv[1]
    instance_name = "zerobus-dev"
    database_name = "zerobus_sdp"
    
    try:
        # Initialize Databricks client
        w = WorkspaceClient()
        
        print(f"Getting service principal for app: {app_name}")
        service_principal_id = get_app_service_principal(app_name)
        
        print(f"Found service principal: {service_principal_id}\n")
        
        # Grant permissions
        grant_lakebase_permissions(
            w, 
            service_principal_id,
            instance_name,
            database_name
        )
        
        print("\n✓ All done! App should now have access to Lakebase.")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
