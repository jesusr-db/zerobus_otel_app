# Suggested Commands

## Critical Rules

### Python Execution
**NEVER use `python` directly - ALWAYS use `uv run`:**
```bash
# ✅ CORRECT
uv run python script.py
uv run uvicorn server.app:app

# ❌ WRONG
python script.py
uvicorn server.app:app
```

### Development Server
**NEVER run the server manually - ALWAYS use `./watch.sh`:**
```bash
# ✅ CORRECT - Start development servers
nohup ./watch.sh > /tmp/databricks-app-watch.log 2>&1 &

# ❌ WRONG - Never run directly
uvicorn server.app:app
```

## Development Lifecycle Commands

### Setup & Installation
```bash
./setup.sh                           # Interactive setup and dependency installation
uv add <package>                     # Add Python dependency
bun add <package>                    # Add frontend dependency
```

### Development
```bash
# Start development servers (frontend:5173, backend:8000)
nohup ./watch.sh > /tmp/databricks-app-watch.log 2>&1 &

# Check logs
tail -f /tmp/databricks-app-watch.log

# Stop development servers
kill $(cat /tmp/databricks-app-watch.pid)
# OR
pkill -f watch.sh
```

### Code Quality
```bash
./fix.sh                            # Format Python (ruff) and TypeScript (prettier)
uv run ruff check .                 # Lint Python
uv run ruff format .                # Format Python
cd client && bun run lint          # Lint TypeScript
cd client && bun run format        # Format TypeScript
```

### Testing & Validation
```bash
# Test API endpoints
curl -s http://localhost:8000/api/endpoint | jq
curl -s http://localhost:8000/docs  # OpenAPI docs

# Test deployed app
uv run python dba_client.py <app-url> /health
uv run python dba_client.py <app-url> /api/user/me
```

### Building
```bash
cd client && bun run build         # Build frontend production bundle
uv run python scripts/make_fastapi_client.py  # Generate TypeScript client
```

### Deployment
```bash
./deploy.sh                        # Deploy to Databricks Apps
databricks bundle deploy --target dev  # Deploy with Databricks CLI
databricks apps list               # List deployed apps
databricks apps get <app-name>     # Get app details

# Monitor deployment logs
uv run python dba_logz.py <app-url> --duration 60
uv run python dba_logz.py <app-url> --search "ERROR|Exception" --duration 30
```

### Git Commands
```bash
git status                         # Check status
git branch                         # List branches
git checkout -b <branch-name>      # Create new branch
git add .                          # Stage all changes
git commit -m "message"            # Commit with message
git push origin <branch>           # Push to remote
```

### Databricks CLI
```bash
databricks current-user me         # Get current user info
databricks apps list               # List apps
databricks secrets list-scopes     # List secret scopes
databricks secrets list-secrets <scope>  # List secrets in scope
```

### macOS System Commands
```bash
# Process management
ps aux | grep <process>            # Find process
lsof -ti:<port> | xargs kill       # Kill process on port
pkill -f <pattern>                 # Kill by pattern

# File operations
find . -name "*.py"                # Find Python files
grep -r "pattern" .                # Search in files
tail -f <file>                     # Follow log file
open <url>                         # Open URL in browser
```

## Directory Navigation
```bash
cd server                          # Backend code
cd client                          # Frontend code
cd docs                            # Documentation
cd scripts                         # Utility scripts
cd resources                       # Databricks bundle resources
```

## Important Paths
- Logs: `/tmp/databricks-app-watch.log`
- PID File: `/tmp/databricks-app-watch.pid`
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
