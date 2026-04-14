# Databricks notebook source
# MAGIC %md
# MAGIC # Ensure Pipeline is Running
# MAGIC
# MAGIC Idempotent check: if the pipeline is already running, exit immediately.
# MAGIC If not running, start it and wait until it reaches a healthy state.
# MAGIC
# MAGIC Used by the `full_pipeline_setup` job to start continuous pipelines
# MAGIC without blocking on completion (continuous pipelines never "complete").

# COMMAND ----------

import time
from databricks.sdk import WorkspaceClient

dbutils.widgets.text("pipeline_id", "", "Pipeline ID")
dbutils.widgets.text("pipeline_name", "", "Pipeline Name (for logging)")

pipeline_id = dbutils.widgets.get("pipeline_id")
pipeline_name = dbutils.widgets.get("pipeline_name") or pipeline_id

if not pipeline_id:
    raise ValueError("pipeline_id is required")

w = WorkspaceClient()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check current pipeline state

# COMMAND ----------

pipeline = w.pipelines.get(pipeline_id)
state = pipeline.state.value if pipeline.state else "UNKNOWN"
print(f"Pipeline: {pipeline_name}")
print(f"  ID: {pipeline_id}")
print(f"  State: {state}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Start if not running

# COMMAND ----------

if state == "RUNNING":
    print(f"\n✅ Pipeline '{pipeline_name}' is already running. Nothing to do.")
    dbutils.notebook.exit(f'{{"status": "already_running", "pipeline_id": "{pipeline_id}"}}')

elif state in ("IDLE", "FAILED", "UNKNOWN"):
    print(f"\n🚀 Starting pipeline '{pipeline_name}' (current state: {state})...")

    # Start a pipeline update (for continuous pipelines, this starts continuous processing)
    update = w.pipelines.start_update(pipeline_id=pipeline_id)
    update_id = update.update_id
    print(f"  Update started: {update_id}")

    # Wait for pipeline to reach RUNNING state (not waiting for update to complete)
    max_wait_seconds = 600  # 10 minutes
    poll_interval = 15
    elapsed = 0

    while elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval

        pipeline = w.pipelines.get(pipeline_id)
        state = pipeline.state.value if pipeline.state else "UNKNOWN"
        print(f"  [{elapsed}s] Pipeline state: {state}")

        if state == "RUNNING":
            print(f"\n✅ Pipeline '{pipeline_name}' is now running.")
            dbutils.notebook.exit(f'{{"status": "started", "pipeline_id": "{pipeline_id}", "update_id": "{update_id}"}}')

        if state == "FAILED":
            # Get the latest update for error details
            events = w.pipelines.list_pipeline_events(pipeline_id=pipeline_id, max_results=5)
            error_msgs = []
            for event in events:
                if event.error:
                    error_msgs.append(str(event.error))
            error_detail = "; ".join(error_msgs[:3]) if error_msgs else "unknown error"
            raise Exception(f"Pipeline '{pipeline_name}' failed: {error_detail}")

    raise Exception(f"Pipeline '{pipeline_name}' did not reach RUNNING state within {max_wait_seconds}s (last state: {state})")

elif state == "STARTING":
    print(f"\n⏳ Pipeline '{pipeline_name}' is already starting. Waiting for RUNNING...")

    max_wait_seconds = 600
    poll_interval = 15
    elapsed = 0

    while elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval

        pipeline = w.pipelines.get(pipeline_id)
        state = pipeline.state.value if pipeline.state else "UNKNOWN"
        print(f"  [{elapsed}s] Pipeline state: {state}")

        if state == "RUNNING":
            print(f"\n✅ Pipeline '{pipeline_name}' is now running.")
            dbutils.notebook.exit(f'{{"status": "already_starting", "pipeline_id": "{pipeline_id}"}}')

        if state == "FAILED":
            raise Exception(f"Pipeline '{pipeline_name}' failed while starting")

    raise Exception(f"Pipeline '{pipeline_name}' did not reach RUNNING state within {max_wait_seconds}s")

else:
    print(f"\n⚠️  Unexpected pipeline state: {state}. Attempting to start...")
    w.pipelines.start_update(pipeline_id=pipeline_id)
    time.sleep(30)
    pipeline = w.pipelines.get(pipeline_id)
    state = pipeline.state.value if pipeline.state else "UNKNOWN"
    if state == "RUNNING":
        print(f"✅ Pipeline '{pipeline_name}' is now running.")
        dbutils.notebook.exit(f'{{"status": "started", "pipeline_id": "{pipeline_id}"}}')
    else:
        raise Exception(f"Pipeline '{pipeline_name}' in unexpected state after start attempt: {state}")
