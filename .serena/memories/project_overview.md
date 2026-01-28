# Project Overview: o11yApp

## Purpose
Observability dashboard for Databricks Apps - a modern full-stack application for monitoring distributed systems with traces, metrics, and logs visualization.

## Key Features
- Service dependency graph visualization
- Distributed trace analysis with waterfall views
- Real-time metrics and KPI monitoring
- Log aggregation and search
- Service health monitoring
- Time-based investigation views

## Data Backend
Currently using **Lakebase** (PostgreSQL) as the data backend:
- Database: `zerobus_sdp`
- Instance: `zerobus-dev`
- Tables: `traces_assembled_synced`, `service_dependencies_synced`, `metrics_1min_synced`, `logs_synced`

## Deployment Target
Databricks Apps platform with Unity Catalog integration

## Current Branch
`no-otel` - OpenTelemetry instrumentation removed from codebase
