---
description: "Rebuild frontend and deploy to Databricks using DABs"
---

# Rebuild Frontend and Deploy with Databricks Asset Bundles

I'll rebuild the frontend and deploy your app to Databricks using Databricks Asset Bundles (DABs).

## What I'll do:

1. **Rebuild frontend** - Clean build of React app with Vite + Bun
2. **Deploy with DABs** - Use `databricks bundle deploy` to sync and deploy
3. **Run the app** - Use `databricks bundle run` to start/restart the app
4. **Monitor deployment** - `databricks apps logs db-chatbot-dev-jesus-rodriguez --follow | grep error` Check logs and verify successful startup
5. **Provide app URL** - Give you the deployed app URL

## Rebuild and Deploy Workflow

### Step 1: Rebuild Frontend

```bash
# Navigate to client directory
cd client

# Clean previous build
rm -rf dist

# Install dependencies if needed
bun install

# Build production frontend
bun run build

# Verify build output
ls -lh dist/

# Return to project root
cd ..
```

**What this does:**
- Cleans old build artifacts
- Ensures dependencies are current
- Builds optimized production bundle
- Creates static assets in `client/dist/`

### Step 2: Deploy with DABs

```bash
# Deploy using Databricks Asset Bundles
databricks bundle deploy
```

**What this does:**
- Uploads bundle files to Databricks workspace
- Syncs code to `.bundle/o11y-jmr/dev/files`
- Deploys resources defined in `databricks.yml`
- Creates/updates app deployment
- Shows deployment status and completion

**Expected output:**
```
Uploading bundle files to /Workspace/Users/.../.bundle/o11y-jmr/dev/files...
Deploying resources...
Updating deployment state...
Deployment complete!
```

### Step 3: Run the App

```bash
# Start/restart the app
databricks bundle run o11y_jmr_app
```

**What this does:**
- Triggers the app to start (if stopped)
- Restarts the app with new code (if already running)
- Waits for app to reach RUNNING state
- Returns when app is successfully started

### Step 4: Monitor Deployment

```bash
databricks apps logs o11y_jmr_app --follow | grep error
```

**What to look for:**
- Any Errors in deployment - that can be leveraged to troubleshoot further

## Usage

Simply run this skill with:
```
/rebuild-deploy
```

Or in conversation:
```
"rebuild and deploy the app"
"redeploy with fresh frontend"
"rebuild frontend and push to databricks"
```

## When to Use This

Use this skill when:
- ✅ You've made frontend changes (React components, UI updates)
- ✅ You've updated frontend dependencies
- ✅ You want to ensure a clean frontend build
- ✅ You're seeing cached/stale frontend code
- ✅ You want the full rebuild + deploy workflow

**Don't use if:**
- ❌ Only backend changes (just use `databricks bundle deploy`)
- ❌ No changes at all (unnecessary rebuild)

## Build vs Deploy vs Run

**`bun run build`** (Frontend only):
- Compiles React + TypeScript
- Bundles with Vite
- Creates static assets
- Does NOT deploy

**`databricks bundle deploy`** (Sync + Deploy):
- Uploads all files to workspace
- Creates/updates app configuration
- Deploys the app
- Does NOT restart automatically

**`databricks bundle run o11y_jmr_app`** (Start/Restart):
- Starts the app if stopped
- Restarts with new code if running
- Waits for RUNNING state

## Full Command Sequence

```bash
# Complete rebuild and deploy workflow
cd client && \
  rm -rf dist && \
  bun install && \
  bun run build && \
  cd .. && \
  databricks bundle deploy && \
  databricks bundle run o11y_jmr_app
```

## Troubleshooting

**Frontend build fails:**
```bash
# Check for TypeScript errors
cd client
bun run lint

# Clean node_modules and rebuild
rm -rf node_modules dist
bun install
bun run build
```

**Bundle deploy fails:**
```bash
# Verify authentication
databricks current-user me

# Check bundle validation
databricks bundle validate

# View bundle configuration
cat databricks.yml
```

**Bundle run fails:**
```bash
# Check app status
databricks apps get o11y-jmr

# Check logs for errors
databricks apps logs db-chatbot-dev-jesus-rodriguez --follow | grep error

# Try manual restart
databricks apps stop o11y-jmr
databricks apps start o11y-jmr
```

**App doesn't start:**
```bash
# Check for Python exceptions in logs
databricks apps logs db-chatbot-dev-jesus-rodriguez --follow | grep error
```

## Post-Deployment Verification

After deployment completes, I'll verify:

1. **App is running:**
   ```bash
   databricks apps get o11y-jmr --output json | jq '.compute_status.state'
   # Expected: "ACTIVE"
   ```

2. **Deployment succeeded:**
   ```bash
   databricks apps get o11y-jmr --output json | jq '.active_deployment.status.state'
   # Expected: "SUCCEEDED"
   ```

3. **App is accessible:**
   ```bash
   curl -I <app-url>
   # Expected: HTTP 200 or 302 (redirect to login)
   ```

4. **Logs show startup:**
   - "Application startup complete"
   - "Uvicorn running on http://0.0.0.0:8000"

## Success Criteria

Deployment is successful when:
- ✅ Frontend built successfully (`client/dist/` exists)
- ✅ Bundle deployed without errors
- ✅ App run command completed
- ✅ Compute status is "ACTIVE"
- ✅ Deployment status is "SUCCEEDED"
- ✅ Logs show uvicorn startup
- ✅ App URL is accessible

## What Gets Deployed

**Frontend:**
- React app built with Vite
- Static assets in `client/dist/`
- Served by FastAPI StaticFiles

**Backend:**
- FastAPI application
- Python dependencies from pyproject.toml
- Server-side routers and logic

**Configuration:**
- Environment variables from `app.yml`
- Resources (SQL Warehouse, Lakebase)
- Compute size and permissions

## Performance Notes

**Typical timings:**
- Frontend build: 5-15 seconds
- Bundle deploy: 30-60 seconds
- App run: 60-120 seconds (includes startup)
- Total: 2-4 minutes end-to-end

**Optimization tips:**
- Frontend already built? Skip rebuild, just deploy
- No frontend changes? Skip rebuild entirely
- Backend only? Use `databricks bundle deploy` alone

## Next Steps After Deployment

1. **Test your app** at the provided URL
2. **Verify changes** are visible in the UI
3. **Check logs** for any warnings or errors
4. **Monitor performance** using the dashboard
5. **Iterate** as needed with quick redeploys

Your app is now deployed with the latest frontend! 🚀
