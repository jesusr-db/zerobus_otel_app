# Task Completion Checklist

## Before Marking Task Complete

### 1. Code Quality
- [ ] Run `./fix.sh` to format all code
- [ ] Check for linting errors with `uv run ruff check .`
- [ ] Verify no TypeScript errors: `cd client && bun run type-check`
- [ ] Remove any `console.log()` or debug code
- [ ] Remove any temporary files or scripts

### 2. Testing & Validation

#### For Backend Changes
- [ ] Test endpoint with curl:
  ```bash
  curl -s http://localhost:8000/api/endpoint | jq
  ```
- [ ] Verify response structure matches expected schema
- [ ] Check FastAPI docs: http://localhost:8000/docs
- [ ] Review logs for errors: `tail -f /tmp/databricks-app-watch.log`

#### For Frontend Changes
- [ ] Test in browser at http://localhost:5173
- [ ] Check browser console for errors (F12)
- [ ] Verify responsive design (mobile, tablet, desktop)
- [ ] Test user interactions and edge cases
- [ ] Use React Query DevTools to verify data fetching

#### For Database Changes
- [ ] Verify query works with test data
- [ ] Check both Lakebase and Warehouse backends (if applicable)
- [ ] Validate result set structure
- [ ] Test with different time ranges

### 3. Git Workflow
- [ ] Stage changes: `git add .`
- [ ] Review changes: `git diff --staged`
- [ ] Commit with descriptive message: `git commit -m "descriptive message"`
- [ ] Include Co-Author if applicable:
  ```
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

### 4. Deployment Verification (If Deploying)
- [ ] Run `./deploy.sh` or `databricks bundle deploy --target dev`
- [ ] Monitor logs for 60 seconds:
  ```bash
  uv run python dba_logz.py <app-url> --duration 60
  ```
- [ ] Verify uvicorn startup messages in logs
- [ ] Check for Python exceptions or errors
- [ ] Test deployed endpoint:
  ```bash
  uv run python dba_client.py <app-url> /health
  uv run python dba_client.py <app-url> /api/endpoint
  ```

### 5. Documentation
- [ ] Update CLAUDE.md if workflow changes
- [ ] Update docs/PROJECT_PLAN.md for significant features
- [ ] Add inline comments for complex logic
- [ ] Update API documentation if endpoints changed

### 6. Cleanup
- [ ] Remove temporary files
- [ ] Delete debug scripts from `claude_scripts/`
- [ ] Clean up commented-out code
- [ ] Verify `.gitignore` excludes temp files

## Common Post-Task Actions

### After Feature Implementation
1. Run `./fix.sh`
2. Test locally with development server
3. Deploy to dev environment
4. Monitor deployment logs
5. Test deployed version
6. Commit changes with descriptive message

### After Bug Fix
1. Verify fix resolves the issue
2. Test edge cases
3. Run `./fix.sh`
4. Deploy and verify in production
5. Monitor for regressions

### After Refactoring
1. Verify no behavioral changes
2. Run all applicable tests
3. Check performance hasn't degraded
4. Review code diff carefully
5. Update documentation if needed

## Rollback Procedure (If Issues Found)
```bash
# If deployment fails or has critical bugs
git log --oneline -5              # Find previous commit
git checkout <previous-commit>    # Rollback code
./deploy.sh                       # Deploy previous version
git checkout <branch>             # Return to current branch
# Fix issues and redeploy
```

## When Task is Complete
- Report success to user
- Summarize what was changed
- Highlight any important notes or caveats
- Suggest next steps if applicable
