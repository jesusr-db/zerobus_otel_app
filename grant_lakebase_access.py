#!/usr/bin/env python3
"""Grant Lakebase access to the Databricks App's Service Principal."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.database import (
    DatabaseInstanceRole,
    DatabaseInstanceRoleIdentityType,
    DatabaseInstanceRoleMembershipRole,
    DatabaseInstanceRoleAttributes
)

def grant_lakebase_access():
    """Grant the app's service principal access to Lakebase."""
    w = WorkspaceClient()
    
    # Service Principal from the error message
    sp_id = "2b35926f-40c4-4c46-a2d0-bb5981beed09"
    instance_name = "zerobus-dev"
    
    print(f"🔑 Granting Lakebase access...")
    print(f"   Service Principal: {sp_id}")
    print(f"   Lakebase Instance: {instance_name}")
    print()
    
    try:
        # Create database role for the service principal
        role = DatabaseInstanceRole(
            name=sp_id,
            identity_type=DatabaseInstanceRoleIdentityType.SERVICE_PRINCIPAL,
            membership_role=DatabaseInstanceRoleMembershipRole.DATABRICKS_SUPERUSER,
            attributes=DatabaseInstanceRoleAttributes(
                bypassrls=True,
                createdb=True,
                createrole=True
            )
        )
        
        result = w.database.create_database_instance_role(
            instance_name=instance_name,
            database_instance_role=role
        )
        
        print(f"✅ Success! Role created")
        print(f"✅ Service Principal {sp_id[:8]}... can now access Lakebase")
        print()
        print("🧪 Next: Test the validation endpoint")
        print("   https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/connectivity")
        
    except Exception as e:
        error_str = str(e).lower()
        if "already exists" in error_str or "duplicate" in error_str:
            print(f"✅ Role already exists - Service Principal already has access")
            print()
            print("🧪 You can test the validation endpoint now:")
            print("   https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/connectivity")
        else:
            print(f"❌ Error: {e}")
            print()
            print("💡 Troubleshooting:")
            print("   1. Make sure you have admin access to the Lakebase instance")
            print("   2. Verify instance name is 'zerobus-dev'")
            print("   3. Check if the service principal ID is correct")
            raise

if __name__ == "__main__":
    grant_lakebase_access()
