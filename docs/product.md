# Product Requirements Document: Observability Dashboard

## Executive Summary

### Problem Statement
Operations and business stakeholders need real-time visibility into service health, dependencies, and performance metrics to effectively monitor system health and debug issues when they arise. Currently, this data exists in raw form across multiple tables in `jmr_demo.zerobus` but lacks a unified, visual interface for analysis.

### Solution
A modern, dark-themed observability dashboard that provides:
- Interactive service dependency visualization with live health overlays
- Real-time health metrics (latency, duration, errors, request counts)
- Trend analysis with historical baseline comparisons
- Drill-down capabilities for detailed service investigation

### Success Criteria
- Auto-refresh every 30 seconds for near-real-time monitoring
- Support multiple time ranges (15min, 1hr, 24hr)
- All services from `jmr_demo.zerobus` visible and queryable
- Fast query response times using SQL warehouse integration

---

## Target Users

### Primary Users: Operations Teams
- **Need:** Monitor service health across all systems
- **Goal:** Quickly identify degraded services and dependency impacts
- **Usage Pattern:** Dashboard always-on display, rapid drill-downs during incidents

### Secondary Users: Business Stakeholders
- **Need:** Understand system performance and service interactions
- **Goal:** Track key metrics and visualize system architecture
- **Usage Pattern:** Periodic check-ins, high-level overviews

---

## Core Features

### 1. Service Dependency Map (Priority: P0)
**Description:** Interactive node-graph visualization showing service relationships and health status

**Requirements:**
- Display all services as nodes with directional edges showing call relationships
- Source data: `service_dependancy` table (source_service → target_service, call_count)
- Visual indicators:
  - Edge direction shows call flow (A calls B)
  - Node color overlays indicate health status (green/yellow/red based on error rate)
  - Edge thickness represents call volume
- Interactions:
  - Click service node → open detailed side panel
  - Pan and zoom for large service graphs
  - Filter by service name or health status

**Data Sources:**
- `jmr_demo.zerobus.service_dependancy` - dependency relationships
- `jmr_demo.zerobus.*_silver` tables - health metrics for overlay

### 2. Service Health Metrics (Priority: P0)
**Description:** Real-time and historical metrics for each service

**Key Metrics:**
1. **Latency** - P50, P95, P99 response times
2. **Duration** - Average and max request duration
3. **Errors** - Error count and error rate percentage
4. **Request Count** - Total requests and requests per second

**Visualization Requirements:**
- Current values displayed prominently
- Trend charts showing metrics over selected time range
- Historical baseline comparison (vs. previous period)
- Time range selector: 15 minutes, 1 hour, 24 hours
- Auto-refresh every 30 seconds

**Data Sources:**
- `jmr_demo.zerobus.trace_assembled_silver` - trace and span data
- `jmr_demo.zerobus.*_silver` - pre-filtered metric tables
- Requires real-time aggregation: AVG, MAX, COUNT, percentiles

### 3. Service Detail Panel (Priority: P0)
**Description:** Contextual side panel with deep-dive service information

**Contents:**
- Service name and metadata (from trace data)
- All 4 health metrics with trend charts
- Inbound dependencies (services calling this service)
- Outbound dependencies (services this service calls)
- Recent error logs (if available in logs table)
- Health status indicator

**Interactions:**
- Triggered by clicking service in dependency map
- Slide-in from right side of screen
- Close button and click-outside-to-close
- Persistent across time range changes

### 4. Multi-View Layout (Priority: P1)
**Description:** Organized UI with multiple panels for different views

**Views:**
1. **Overview Dashboard** - Summary of all services health
2. **Dependency Map View** - Full-screen interactive graph
3. **Service List View** - Tabular view with sortable metrics
4. **Detail Panel** - Overlay on any view when service selected

**Navigation:**
- Tab-based or sidebar navigation between main views
- Service detail panel overlays on current view
- Maintain selected service across view switches

---

## Technical Requirements

### Data Access
- **Database:** `jmr_demo.zerobus` catalog/schema
- **Primary Tables:**
  - `trace_assembled_silver` - trace and span data with service_name
  - `service_dependancy` - service relationships (source_service, target_service, call_count)
  - `*_silver` tables - filtered metric data
- **SQL Warehouse:** Auto-detect available warehouses, use first available

### Performance
- Initial load: < 3 seconds
- Auto-refresh: every 30 seconds
- Time range changes: < 2 seconds
- Smooth UI interactions (60fps animations)

### Scalability
- Support 100+ services in dependency graph
- Handle high cardinality service names
- Efficient aggregation queries for metrics

---

## UI/UX Requirements

### Visual Design
- **Theme:** Modern dark theme
- **Color Palette:**
  - Healthy: Green (#10b981)
  - Warning: Yellow/Amber (#f59e0b)
  - Critical: Red (#ef4444)
  - Background: Dark grays (#111827, #1f2937)
  - Text: White/light gray
- **Typography:** Clean, modern sans-serif
- **Icons:** Consistent icon set for metrics and actions

### Responsiveness
- Desktop-first design (1920x1080 primary)
- Minimum width: 1280px
- Adaptive layouts for different screen sizes

### Accessibility
- High contrast for readability
- Keyboard navigation support
- Clear focus indicators
- Descriptive labels and tooltips

---

## Success Metrics

### User Adoption
- Daily active users from ops team
- Average session duration > 5 minutes
- Multiple time range selections per session

### Performance
- Query response time < 2 seconds (95th percentile)
- Page load time < 3 seconds
- Zero UI blocking during auto-refresh

### System Health Visibility
- All services in `jmr_demo.zerobus` visible
- Metrics accuracy matches raw data (within 1%)
- Dependency graph completeness (all relationships shown)

---

## Implementation Priority

### Phase 1: MVP (Week 1-2)
- Basic dependency map visualization
- Service health metrics display (current values)
- Simple service detail panel
- Single time range (1 hour)
- SQL warehouse integration

### Phase 2: Enhanced Metrics (Week 3)
- Trend charts for all metrics
- Multiple time ranges (15min, 1hr, 24hr)
- Historical baseline comparison
- Auto-refresh functionality

### Phase 3: Polish & Multi-View (Week 4)
- Overview dashboard view
- Service list view
- Advanced filtering and search
- Performance optimization
- Dark theme refinement

### Future Enhancements (Post-MVP)
- Custom time range picker
- Service health alerting
- Log integration and viewing
- Anomaly detection
- Export capabilities (charts, data)

---

## Out of Scope (Current Release)

- Real-time alerting and notifications
- User authentication and authorization (uses Databricks OAuth)
- Custom dashboard creation
- Historical data export
- Mobile app version
- Integration with external incident management tools
- AI-powered root cause analysis

---

## Assumptions & Dependencies

### Assumptions
- `jmr_demo.zerobus` schema and tables exist and are accessible
- Data quality is sufficient for visualization (no excessive nulls)
- Service names are consistent across tables
- SQL warehouse has sufficient capacity for queries

### Dependencies
- Databricks SQL warehouse availability
- Access to `jmr_demo.zerobus` tables
- Modern browser support (Chrome, Firefox, Safari, Edge)
- OAuth authentication via Databricks Apps

### Risks
- Large number of services (>500) may impact graph performance
- High query frequency (30s refresh) may hit warehouse limits
- Missing or incomplete dependency data may show gaps in graph
- Time-based aggregations may be expensive for 24hr range
