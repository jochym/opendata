# Debugging and Issue Handling Guide

## Universal Rules for Bug Fixes and Issue Resolution

### 1. Branch Strategy (IRON RULE)

**Every issue MUST be worked on a separate branch.** The `main` branch is reserved ONLY for preparing releases.

#### Branch Creation:
```bash
# For bug fixes
git checkout -b fix/issue-<number>-short-description

# For features
git checkout -b feature/short-description

# For documentation
git checkout -b docs/short-description
```

#### Branch Naming Conventions:
- `fix/<description>` - Bug fixes
- `feature/<description>` - New features
- `docs/<description>` - Documentation updates
- `refactor/<description>` - Code refactoring
- `test/<description>` - Test additions/updates

#### NEVER:
- ❌ Commit directly to `main` (except for release preparation)
- ❌ Push to `main` without testing
- ❌ Skip PR review for significant changes

---

### 2. Session Setup Checklist

**Before starting work on any issue:**

```bash
# 1. Clean environment
git checkout main
git pull origin main
git status  # Should be clean

# 2. Check issues
gh issue list

# 3. Create feature branch
git checkout -b fix/issue-<number>

# 4. Set up test environment
pkill -9 -f "python src/opendata/main.py"
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python src/opendata/main.py --host 127.0.0.1 --port 8891 --no-browser --headless &
sleep 5
curl -I http://127.0.0.1:8891  # Verify it's running

# 5. Document reproduction steps
# 6. Write test that fails
# 7. Implement fix
# 8. Verify test passes
# 9. Clean up and commit
```

---

### 3. Systematic Debugging Workflow

#### Step 1: Verify Assumptions Immediately

**Never assume - always verify:**

```bash
# Don't assume app is running - VERIFY
ps aux | grep main.py | grep -v grep
lsof -i :8080
curl -I http://localhost:8080

# Don't assume file is saved - VERIFY
cat ~/.opendata_tool/projects/*/analysis.json | python -m json.tool

# Don't assume model loads correctly - VERIFY
PYTHONPATH=$PYTHONPATH:$(pwd)/src python3 -c "from opendata.models import X; print(X.model_validate_json('{}'))"
```

#### Step 2: Isolate the Problem Layer

```
User sees issue → UI layer? → Check browser (agent-browser)
                          ↓
                    State layer? → Check ctx.session, ScanState
                          ↓
             Persistence layer? → Check JSON files, database
                          ↓
               Model layer? → Test model_validate_json directly
```

#### Step 3: Use the Right Tool for the Job

- **UI issues**: `agent-browser` + snapshots
- **State issues**: Add logging, check `ctx.refresh()` calls
- **Persistence issues**: `cat <file>.json`, test model loading
- **Performance issues**: `ps aux`, check loop operations

#### Step 4: One Change at a Time

1. Make ONE fix
2. Test immediately
3. Verify it works
4. THEN move to next fix

**Never** make 5 changes then test - you won't know which one fixed/broke it.

---

### 4. Common Bug Patterns

#### Pattern 1: "Data Saves But Doesn't Load"

**Symptoms**: Data appears correct in JSON files but shows as empty/defaults in UI after reload.

**Checklist**:
1. ✅ Verify file is actually written: `cat <file>.json | python -m json.tool`
2. ✅ Test model loading directly with Python
3. ✅ Check for `model_config = {"populate_by_name": True}` in Pydantic models with aliases

**Root Cause**: Usually Pydantic `validation_alias` without `populate_by_name=True`.

#### Pattern 2: "UI Doesn't Reflect State Changes"

**Symptoms**: State changes in code but UI shows old values.

**Checklist**:
1. ✅ Verify state is actually changed: Add logging before/after change
2. ✅ Check if component is registered: `ctx.register_refreshable("name", render_func)`
3. ✅ Verify refresh is called: `ctx.refresh("name")` or `render_func.refresh()`
4. ✅ Check for stale closures in lambda handlers

**Root Cause**: Usually missing refresh call or stale closure.

#### Pattern 3: "Dialog/Flickering Issues"

**Symptoms**: Dialog flickers, shows "client deleted" errors, or doesn't stay open.

**Checklist**:
1. ✅ Is dialog created ONCE and stored? Check for `hasattr(ctx, '_dialog')`
2. ✅ Are you recreating dialog on every refresh? Don't do that.
3. ✅ Use timer-based updates instead of manual refresh

**Root Cause**: Recreating NiceGUI components on every refresh instead of updating existing ones.

#### Pattern 4: "Performance/Memory Issues"

**Symptoms**: App slows down or crashes on large datasets.

**Checklist**:
1. ✅ Check for expensive operations in loops
2. ✅ Check UI update frequency - should throttle to 0.5-1.0s
3. ✅ Check for unbounded lists/caches in session state

**Root Cause**: Usually path resolution in loops or too-frequent UI updates.

---

### 5. Testing Requirements

#### Test Categories:
```bash
# CI/CD safe (default, ~5 seconds)
pytest

# All tests including AI (requires API key, ~30 seconds)
pytest -m ""

# Only AI tests (local only)
pytest -m ai_interaction

# Only local tests (requires app running)
pytest -m local_only
```

#### Writing Good Tests:

**GOOD** - Tests CORRECT behavior:
```python
def test_file_role_persists_across_project_switch():
    """File roles (Article/Other) are preserved when switching projects."""
    # Arrange
    agent.add_significant_file("paper.tex", "main_article")
    agent.save_state()
    
    # Act
    agent.load_project(other_path)
    agent.load_project(original_path)
    
    # Assert
    assert agent.current_analysis.file_suggestions[0].reason == "Main article/paper"
```

**BAD** - Tests implementation details:
```python
def test_analysis_json_has_reason_field():
    """Don't test JSON structure, test behavior."""
    # This is too implementation-focused
```

#### Every Bug Fix MUST Include:
- [ ] At least one test that reproduces the bug (fails before fix)
- [ ] Test verifies correct behavior (passes after fix)
- [ ] All existing tests still pass (`pytest`)

---

### 6. Process Management

**Before starting the app:**
```bash
# Kill ALL existing instances
pkill -9 -f "python src/opendata/main.py"
lsof -ti :8080 | xargs -r kill -9
sleep 2
```

**Start on NON-STANDARD PORT for exclusive access:**
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python src/opendata/main.py --host 127.0.0.1 --port 8889 --no-browser --headless > app.log 2>&1 &

# Verify IMMEDIATELY
sleep 5
ps aux | grep main.py | grep -v grep
lsof -i :8889
```

**Why**:
- Multiple instances cause data corruption and unpredictable UI behavior
- `0.0.0.0:8080` is public - use `127.0.0.1:8889` (or any unusual port) for testing
- Always verify the process actually started before testing

---

### 7. Code Review Checklist

#### Before Running Tests:
- [ ] Only one app process running (`ps aux | grep main.py`)
- [ ] Running on localhost:unusual_port (not 0.0.0.0:8080)
- [ ] Working tree is clean OR changes are intentional
- [ ] `PYTHONPATH` is set correctly

#### Before Committing:
- [ ] All tests pass: `pytest`
- [ ] Syntax check passes: `python -m py_compile src/opendata/main.py`
- [ ] App starts: `python src/opendata/main.py --help`
- [ ] No LSP errors in changed files

#### Before Merging to Main:
- [ ] VERSION file updated
- [ ] CHANGELOG.md updated
- [ ] website/index.html updated (version + 4 download links)
- [ ] Documentation synced: `cp docs/*.md website/docs/`
- [ ] Full test suite passes
- [ ] Working tree is clean

---

### 8. Documentation Rules

#### Document as You Go:
- When you find a bug, note the symptom and root cause
- When you fix it, note the pattern for future reference
- Add lessons learned to `docs/SESSION_HANDOFF.md` after each session

#### Session Handoff Updates:
After completing work, update the session handoff document with:
- Problem description
- Root cause analysis
- Solution implemented
- Test coverage added
- Verification commands

---

### 9. Critical File Locations

#### State Persistence:
- `~/.opendata_tool/projects/<id>/analysis.json` - File suggestions with roles
- `~/.opendata_tool/projects/<id>/fingerprint.json` - Significant files list
- `~/.opendata_tool/projects/<id>/metadata.yaml` - Project metadata
- `~/.opendata_tool/projects/<id>/inventory.db` - SQLite file cache

#### Core Logic:
- `src/opendata/agents/project_agent.py` - Project loading, state management
- `src/opendata/agents/parsing.py` - AI response parsing
- `src/opendata/models.py` - Pydantic models (CRITICAL: check for model_config)
- `src/opendata/workspace.py` - Save/load project state

#### UI Components:
- `src/opendata/ui/components/chat.py` - Chat, status modal
- `src/opendata/ui/components/files_dialog.py` - File selection
- `src/opendata/ui/context.py` - AppContext, refreshable registration
- `src/opendata/ui/state.py` - ScanState, UIState

---

### 10. Release Checklist

#### Pre-Release:
- [ ] Run `pytest` - all tests must pass
- [ ] Check working tree is clean
- [ ] Verify no uncommitted debugging code

#### Release Steps:
```bash
# 1. Update version files
echo "0.22.40" > src/opendata/VERSION

# 2. Update CHANGELOG.md (top of file)

# 3. Update website/index.html (version + 4 download links)

# 4. Sync docs
cp docs/*.md website/docs/

# 5. Commit
git add CHANGELOG.md src/opendata/VERSION website/index.html
git commit -m "chore: prepare for v0.22.40 release"
git push origin fix/branch

# 6. Merge to main (from main branch)
git checkout main
git merge fix/branch --no-ff -m "Release v0.22.40"
git push origin main

# 7. Tag and release
git tag v0.22.40
git push origin v0.22.40

cat << 'EOF' | gh release create v0.22.40 --title "v0.22.40 - Description" --notes-file -
## Release Notes
...
EOF

# 8. Verify CI/CD
gh run list --limit 3 --branch main
gh run view <run-id> --json conclusion
```

#### Post-Release:
- [ ] Verify website updated
- [ ] Verify release assets
- [ ] Delete feature branch
- [ ] Clean working tree

---

**Last Updated**: 2026-03-05  
**Version**: v0.22.40
