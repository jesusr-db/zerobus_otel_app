# Databricks notebook source
# MAGIC %md
# MAGIC # Grant Lakebase Permissions to App Service Principal
# MAGIC 
# MAGIC This notebook:
# MAGIC 1. Gets the service principal ID from the deployed app
# MAGIC 2. Uses Databricks Secrets to connect to Lakebase
# MAGIC 3. Grants necessary permissions on database, schema, and tables

# COMMAND ----------

# MAGIC %pip install --upgrade psycopg2-binary databricks-sdk

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import json
from databricks.sdk import WorkspaceClient
import psycopg2

# COMMAND ----------

# Configuration from job parameters
try:
    app_name = dbutils.widgets.get("APP_NAME")
except:
    app_name = "o11y-jmr"

try:
    instance_name = dbutils.widgets.get("LAKEBASE_INSTANCE_NAME")
except:
    instance_name = "zerobus-dev"

try:
    lakebase_host = dbutils.widgets.get("LAKEBASE_HOST")
except:
    lakebase_host = "instance-c33627a6-422c-461a-82f7-ac78b0a6d72a.database.cloud.databricks.com"

try:
    lakebase_port = int(dbutils.widgets.get("LAKEBASE_PORT"))
except:
    lakebase_port = 5432

try:
    lakebase_database = dbutils.widgets.get("LAKEBASE_DATABASE_NAME")
except:
    lakebase_database = "zerobus_sdp"

try:
    lakebase_schema = dbutils.widgets.get("LAKEBASE_SCHEMA_NAME")
except:
    lakebase_schema = "zerobus_sdp"

print(f"Configuration:")
print(f"  App Name: {app_name}")
print(f"  Instance: {instance_name}")
print(f"  Host: {lakebase_host}")
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

# Define grants
grants = [
    f'GRANT CONNECT ON DATABASE {lakebase_database} TO "{sp_client_id}"',
    f'GRANT USAGE ON SCHEMA {lakebase_schema} TO "{sp_client_id}"',
    f'GRANT SELECT ON ALL TABLES IN SCHEMA {lakebase_schema} TO "{sp_client_id}"',
    f'ALTER DEFAULT PRIVILEGES IN SCHEMA {lakebase_schema} GRANT SELECT ON TABLES TO "{sp_client_id}"',
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
