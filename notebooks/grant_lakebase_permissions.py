# Databricks notebook source
# MAGIC %md
# MAGIC # Grant Lakebase Permissions to App Service Principal
# MAGIC 
# MAGIC This notebook:
# MAGIC 1. Gets the service principal ID from the deployed app
# MAGIC 2. Uses Databricks Secrets to connect to Lakebase
# MAGIC 3. Grants necessary permissions on database, schema, and tables

# COMMAND ----------

import json
from databricks.sdk import WorkspaceClient
import psycopg2

# COMMAND ----------

# Configuration from job parameters
dbutils.widgets.text("APP_NAME", "o11y-jmr", "App Name")
dbutils.widgets.text("LAKEBASE_INSTANCE_NAME", "zerobus-dev", "Lakebase Instance")
dbutils.widgets.text("LAKEBASE_DATABASE_NAME", "zerobus_sdp", "Database Name")
dbutils.widgets.text("LAKEBASE_SCHEMA_NAME", "zerobus_sdp", "Schema Name")

app_name = dbutils.widgets.get("APP_NAME")
instance_name = dbutils.widgets.get("LAKEBASE_INSTANCE_NAME")
lakebase_database = dbutils.widgets.get("LAKEBASE_DATABASE_NAME")
lakebase_schema = dbutils.widgets.get("LAKEBASE_SCHEMA_NAME")
lakebase_port = 5432

print(f"Configuration:")
print(f"  App Name: {app_name}")
print(f"  Instance: {instance_name}")
print(f"  Database: {lakebase_database}")
print(f"  Schema: {lakebase_schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Get App Service Principal using SDK

# COMMAND ----------

import uuid

# Initialize WorkspaceClient
w = WorkspaceClient()

print(f"Getting service principal for app: {app_name}")

# Get app info
app = w.apps.get(app_name)
sp_client_id = app.service_principal_client_id
sp_id = app.service_principal_id
sp_name = app.service_principal_name

print(f"\nService Principal:")
print(f"  Client ID: {sp_client_id}")
print(f"  SP ID: {sp_id}")
print(f"  Name: {sp_name}")

if not sp_client_id:
    raise Exception("Could not get service principal client ID from app")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Get Lakebase Instance and Generate Credentials

# COMMAND ----------

print(f"Getting Lakebase instance: {instance_name}")

# Get instance details
instance = w.database.get_database_instance(name=instance_name)

print(f"Instance DNS: {instance.read_write_dns}")

# Generate database credential
print(f"Generating database credential...")
cred = w.database.generate_database_credential(
    request_id=str(uuid.uuid4()),
    instance_names=[instance_name]
)

print("Credential generated successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect to Lakebase and Grant Permissions

# COMMAND ----------

print(f"\nConnecting to Lakebase...")
print(f"  Host: {instance.read_write_dns}")
print(f"  Database: {lakebase_database}")
print(f"  Schema: {lakebase_schema}")

# Get the current user's identity (the job's service principal)
current_user = w.current_user.me()
job_user_name = current_user.user_name

print(f"  Connecting as: {job_user_name}")

# The app's service principal name (not client ID) is used as role in Lakebase
print(f"  App SP Name: {sp_name}")
print(f"  App SP Client ID: {sp_client_id}")

# Connect to Lakebase using:
# - user: job's service principal (current user)
# - password: generated credential token
conn = psycopg2.connect(
    host=instance.read_write_dns,
    port=lakebase_port,
    dbname=lakebase_database,
    user=job_user_name,
    password=cred.token,
    sslmode='require'
)

cur = conn.cursor()

# List existing roles to find the correct one for the app SP
print("\nListing database roles...")
cur.execute("SELECT rolname FROM pg_roles ORDER BY rolname")
roles = [row[0] for row in cur.fetchall()]
print(f"  Found {len(roles)} roles")

# Find matching role for our SP (could be client_id, sp_name, or prefixed)
matching_roles = [r for r in roles if sp_client_id in r or (sp_name and sp_name.replace(' ', '') in r.replace(' ', ''))]
print(f"  Matching roles for SP: {matching_roles}")

# Determine which role identifier to use
if sp_client_id in roles:
    role_id = sp_client_id
    print(f"  Using client ID as role: {role_id}")
elif matching_roles:
    role_id = matching_roles[0]
    print(f"  Using matching role: {role_id}")
else:
    # Print all roles for debugging
    print(f"  WARNING: No matching role found for SP")
    print(f"  Available roles: {roles[:20]}...")  # Show first 20
    role_id = sp_client_id  # Fall back to client ID

# Define grants
grants = [
    f'GRANT CONNECT ON DATABASE {lakebase_database} TO "{role_id}"',
    f'GRANT USAGE ON SCHEMA {lakebase_schema} TO "{role_id}"',
    f'GRANT SELECT ON ALL TABLES IN SCHEMA {lakebase_schema} TO "{role_id}"',
    f'ALTER DEFAULT PRIVILEGES IN SCHEMA {lakebase_schema} GRANT SELECT ON TABLES TO "{role_id}"',
]

print(f"\nGranting permissions to service principal: {sp_client_id}")

results = []
for grant in grants:
    try:
        print(f"  Executing: {grant}")
        cur.execute(grant)
        conn.commit()
        print("    ✓ Success")
        results.append({"statement": grant, "status": "success"})
    except Exception as e:
        print(f"    ⚠ Warning: {e}")
        conn.rollback()
        results.append({"statement": grant, "status": f"warning: {e}"})

cur.close()
conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "="*60)
print("PERMISSIONS GRANT COMPLETE")
print("="*60)
print(f"App: {app_name}")
print(f"Service Principal: {sp_client_id}")
print(f"Database: {lakebase_database}")
print(f"Schema: {lakebase_schema}")
print("\nGrant Results:")
for result in results:
    status_symbol = "✓" if result["status"] == "success" else "⚠"
    print(f"  {status_symbol} {result['status']}")
print("="*60)

dbutils.notebook.exit(json.dumps({
    "app_name": app_name,
    "service_principal_client_id": sp_client_id,
    "database": lakebase_database,
    "schema": lakebase_schema,
    "results": results
}))
