# Lakebase Permission Issue - Fix Guide

## 🔍 Issue Identified

**Error**: `FATAL: role "2b35926f-40c4-4c46-a2d0-bb5981beed09" does not exist`

**Root Cause**: The Databricks App's Service Principal doesn't have permission to access the Lakebase instance `zerobus-dev`.

**Service Principal ID**: `2b35926f-40c4-4c46-a2d0-bb5981beed09`

## ✅ Solution: Grant Lakebase Access

### Option 1: Using Databricks SDK (Python)

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Grant the app's service principal access to Lakebase
w.database.create_database_instance_role(
    instance_name="zerobus-dev",
    database_instance_role={
        "name": "2b35926f-40c4-4c46-a2d0-bb5981beed09",  # App's Service Principal
        "identity_type": "SERVICE_PRINCIPAL",
        "membership_role": "DATABRICKS_USER",  # or DATABRICKS_SUPERUSER for full access
        "attributes": {
            "bypassrls": False,
            "createdb": False,
            "createrole": False
        }
    }
)

print("✅ Permission granted to Service Principal")
```

### Option 2: Using Databricks CLI

```bash
# Create a role for the service principal on Lakebase
databricks database create-database-instance-role \
  --instance-name zerobus-dev \
  --json '{
    "name": "2b35926f-40c4-4c46-a2d0-bb5981beed09",
    "identity_type": "SERVICE_PRINCIPAL",
    "membership_role": "DATABRICKS_USER"
  }'
```

### Option 3: Using Databricks UI

1. Go to **Compute** → **Lakebase** in Databricks workspace
2. Click on instance `zerobus-dev`
3. Go to **Permissions** tab
4. Click **Add Permissions**
5. Search for Service Principal: `2b35926f-40c4-4c46-a2d0-bb5981beed09`
6. Grant permission level: **CAN_USE** or **CAN_MANAGE**

### Option 4: Using SQL (from Databricks notebook)

```sql
-- Grant the service principal access to the Lakebase instance
GRANT USAGE ON DATABASE zerobus_dev 
TO SERVICE_PRINCIPAL '2b35926f-40c4-4c46-a2d0-bb5981beed09';

-- Grant access to the specific database
GRANT USAGE, SELECT ON DATABASE databricks_postgres 
TO SERVICE_PRINCIPAL '2b35926f-40c4-4c46-a2d0-bb5981beed09';

-- Grant access to schemas
GRANT USAGE, SELECT ON SCHEMA zerobus_sdp 
TO SERVICE_PRINCIPAL '2b35926f-40c4-4c46-a2d0-bb5981beed09';
```

## 🚀 Quick Fix Script

Save this as `grant_lakebase_access.py` and run it:

```python
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
    
    print(f"Granting access to Service Principal: {sp_id}")
    print(f"Lakebase Instance: {instance_name}")
    
    try:
        # Create database role for the service principal
        role = DatabaseInstanceRole(
            name=sp_id,
            identity_type=DatabaseInstanceRoleIdentityType.SERVICE_PRINCIPAL,
            membership_role=DatabaseInstanceRoleMembershipRole.DATABRICKS_USER,
            attributes=DatabaseInstanceRoleAttributes(
                bypassrls=False,
                createdb=False,
                createrole=False
            )
        )
        
        result = w.database.create_database_instance_role(
            instance_name=instance_name,
            database_instance_role=role
        )
        
        print(f"✅ Success! Role created: {result}")
        print(f"✅ Service Principal {sp_id} can now access Lakebase instance {instance_name}")
        
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"✅ Role already exists - Service Principal already has access")
        else:
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    grant_lakebase_access()
```

Run it:
```bash
python grant_lakebase_access.py
```

## 🔄 After Granting Permissions

1. **No need to redeploy** - The app is already running
2. **Just retry the validation endpoint**:
   ```
   https://o11y-jmr-1351565862180944.aws.databricksapps.com/api/lakebase-validation/connectivity
   ```

3. **Expected result after permission granted**:
   ```json
   {
     "overall_status": true,
     "connectivity": {
       "warehouse": {"connected": true},
       "lakebase": {"connected": true}
     }
   }
   ```

## 📋 Verification Checklist

After granting permissions:

- [ ] Connectivity test passes (`overall_status: true`)
- [ ] Lakebase connection successful
- [ ] OAuth token refresh working
- [ ] Test query returns data
- [ ] Services query comparison works

## 🔍 Troubleshooting

### If permission grant fails:

**Error**: "Insufficient privileges"
**Solution**: Make sure you have admin access to the Lakebase instance

**Error**: "Instance not found"
**Solution**: Verify instance name is exactly `zerobus-dev`

**Error**: "Invalid identity type"
**Solution**: Ensure using `SERVICE_PRINCIPAL` not `USER`

### If still getting "role does not exist":

1. Check if role was created:
   ```bash
   databricks database list-database-instance-roles --instance-name zerobus-dev
   ```

2. Verify the Service Principal ID matches:
   ```bash
   # From the error message, should be:
   2b35926f-40c4-4c46-a2d0-bb5981beed09
   ```

3. Wait 30 seconds for permissions to propagate, then retry

## 📚 Understanding the Error

**What happened**:
- App deployed with Service Principal: `2b35926f-40c4-4c46-a2d0-bb5981beed09`
- App tried to connect to Lakebase as this Service Principal
- PostgreSQL checked for a role named `2b35926f-40c4-4c46-a2d0-bb5981beed09`
- Role didn't exist → connection refused

**Why it's fixable**:
- This is a permission issue, not a code issue
- Once the role is created in Lakebase, connections will work
- No code or deployment changes needed

## 🎯 Next Steps

1. Grant permissions using one of the methods above
2. Retry validation endpoint
3. Check logs for successful connection
4. Proceed with query validation and comparison

---

**Everything else is working perfectly!** The only issue is the missing Lakebase permission.
