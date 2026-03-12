# OpenData Tool - Session Handoff Guide (v0.22.39)

## 🎯 Purpose

This document contains **universal lessons and practical patterns** learned from fixing bugs in the OpenData Tool. It focuses on actionable knowledge for future debugging sessions, not specific bug details.

---

## ⚡ Critical Session Setup

### 1. Process Management (ALWAYS DO THIS FIRST)
```bash
# Kill ALL existing instances before starting
pkill -9 -f "python src/opendata/main.py"
lsof -ti :8080 | xargs -r kill -9
sleep 2

# Start on NON-STANDARD PORT for exclusive access
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python src/opendata/main.py --host 127.0.0.1 --port 8889 --no-browser --headless > app.log 2>&1 &

# Verify IMMEDIATELY
sleep 5
ps aux | grep main.py | grep -v grep
lsof -i :8889
curl -I http://127.0.0.1:8889
```

**Why**: 
- Multiple instances cause data corruption and unpredictable UI behavior
- `0.0.0.0:8080` is public - use `127.0.0.1:8889` (or any unusual port) for testing
- Always verify the process actually started before testing

### 2. agent-browser Testing Workflow

```bash
# Open and wait for full load
agent-browser open http://127.0.0.1:8889
agent-browser wait 10000  # Wait longer than you think necessary

# Take snapshot to see interactive elements
agent-browser snapshot -i -C

# For dropdowns/menus, wait extra time
agent-browser click @e1  # Click dropdown
agent-browser wait 5000  # Wait for animation
agent-browser snapshot -i -C  # Get fresh refs

# Common patterns:
agent-browser fill @e14 "/path/to/project"  # Fill textbox
agent-browser press Enter                    # Press Enter
agent-browser click @e19                     # Click button
agent-browser wait 3000                      # Wait for action
agent-browser snapshot -i -C                 # Check result
```

**Key Lessons**:
- Elements get new refs after EVERY page change - always re-snapshot
- Dropdowns need 3-5 seconds to fully render
- If action "times out", the element ref is stale - snapshot again
- Use `-C` flag to see cursor-interactive elements (divs with onclick)

---

## 🐛 Bug Investigation Patterns

### Pattern 1: "Data Saves But Doesn't Load"

**Symptoms**: Data appears correct in JSON files but shows as empty/defaults in UI after reload.

**Checklist**:
1. ✅ Verify file is actually written: `cat <file>.json | python -m json.tool`
2. ✅ Test model loading directly:
   ```bash
   cd /home/jochym/Projects/OpenData
   PYTHONPATH=$PYTHONPATH:$(pwd)/src python3 << 'EOF'
   from opendata.models import AIAnalysis
   from pathlib import Path
   
   with open("/path/to/analysis.json", "r") as f:
       data = f.read()
   
   try:
       obj = AIAnalysis.model_validate_json(data)
       print(f"Loaded: {len(obj.file_suggestions)} suggestions")
       for fs in obj.file_suggestions:
           print(f"  {fs.path}: {fs.reason}")
   except Exception as e:
       print(f"ERROR: {e}")
   EOF
   ```
3. ✅ Check for `model_config = {"populate_by_name": True}` in Pydantic models with aliases

**Root Cause**: Usually Pydantic `validation_alias` without `populate_by_name=True`.

### Pattern 2: "UI Doesn't Reflect State Changes"

**Symptoms**: State changes in code but UI shows old values.

**Checklist**:
1. ✅ Verify state is actually changed: Add logging before/after change
2. ✅ Check if component is registered: `ctx.register_refreshable("name", render_func)`
3. ✅ Verify refresh is called: `ctx.refresh("name")` or `render_func.refresh()`
4. ✅ Check for stale closures in lambda handlers - capture variables properly:
   ```python
   # BAD - captures loop variable by reference
   for item in items:
       btn.on_click=lambda _: handler(item)
   
   # GOOD - captures by value
   for item in items:
       btn.on_click=(lambda x: lambda _: handler(x))(item)
   ```

**Root Cause**: Usually missing refresh call or stale closure.

### Pattern 3: "Dialog/Flickering Issues"

**Symptoms**: Dialog flickers, shows "client deleted" errors, or doesn't stay open.

**Checklist**:
1. ✅ Is dialog created ONCE and stored? Check for `hasattr(ctx, '_dialog')`
2. ✅ Are you recreating dialog on every refresh? Don't do that.
3. ✅ Use timer-based updates instead of manual refresh:
   ```python
   # GOOD pattern
   def render_dialog(ctx):
       if not hasattr(ctx, '_dialog'):
           with ui.dialog() as dialog:
               spinner = ui.spinner()
               label = ui.label()
           ctx._dialog = dialog
           
           def update():
               # Update label text, visibility, etc.
               pass
           
           ui.timer(0.5, update)
       
       if is_active:
           ctx._dialog.open()
   ```

**Root Cause**: Recreating NiceGUI components on every refresh instead of updating existing ones.

### Pattern 4: "Performance/Memory Issues"

**Symptoms**: App slows down or crashes on large datasets.

**Checklist**:
1. ✅ Check for expensive operations in loops:
   ```python
   # BAD - resolves path twice per file
   for p, stat in walk_project_files(root):
       rel_path = str(p.resolve().relative_to(root.resolve()))
   
   # GOOD - cache root resolution
   root_abs = str(root.absolute())
   for p, stat in walk_project_files(root):
       p_abs = str(p)
       rel_path = p_abs[len(root_abs):].lstrip("/") if p_abs.startswith(root_abs) else p.name
   ```
2. ✅ Check UI update frequency - should throttle to 0.5-1.0s
3. ✅ Check for unbounded lists/caches in session state

**Root Cause**: Usually path resolution in loops or too-frequent UI updates.

---

## 🔧 Code Review Checklist

### Before Running Tests
- [ ] Only one app process running (`ps aux | grep main.py`)
- [ ] Running on localhost:unusual_port (not 0.0.0.0:8080)
- [ ] Working tree is clean OR changes are intentional
- [ ] `PYTHONPATH` is set correctly

### Before Committing
- [ ] All tests pass: `pytest`
- [ ] Syntax check passes: `python -m py_compile src/opendata/main.py`
- [ ] App starts: `python src/opendata/main.py --help`
- [ ] No LSP errors in changed files (ignore false positives for refreshable)

### Before Merging to Main
- [ ] VERSION file updated
- [ ] CHANGELOG.md updated
- [ ] website/index.html updated (version + download links)
- [ ] Documentation synced: `cp docs/*.md website/docs/`
- [ ] Full test suite passes
- [ ] Working tree is clean

---

## 🧪 Testing Best Practices

### Test Categories
```bash
# CI/CD safe (default, ~5 seconds)
pytest

# All tests including AI (requires API key, ~30 seconds)
pytest -m ""

# Only AI tests (local only)
pytest -m ai_interaction

# Only local tests (requires app running)
pytest -m local_only

# Specific test file
pytest tests/unit/agents/test_parsing.py

# Specific test function
pytest tests/unit/agents/test_parsing.py -k "test_yaml_list_based"
```

### Writing Good Tests
```python
# GOOD - Tests CORRECT behavior
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

# BAD - Tests implementation details
def test_analysis_json_has_reason_field():
    """Don't test JSON structure, test behavior."""
    # This is too implementation-focused
```

### Debugging Test Failures
1. Run single test: `pytest tests/unit/test.py::test_function -v`
2. Add print statements to test
3. Check if test expects CORRECT behavior vs CURRENT behavior
4. Verify test fixtures are set up correctly

---

## 📁 Critical File Locations

### State Persistence
- `~/.opendata_tool/projects/<id>/analysis.json` - File suggestions with roles
- `~/.opendata_tool/projects/<id>/fingerprint.json` - Significant files list
- `~/.opendata_tool/projects/<id>/metadata.yaml` - Project metadata
- `~/.opendata_tool/projects/<id>/inventory.db` - SQLite file cache

### Core Logic
- `src/opendata/agents/project_agent.py` - Project loading, state management
- `src/opendata/agents/parsing.py` - AI response parsing
- `src/opendata/models.py` - Pydantic models (CRITICAL: check for model_config)
- `src/opendata/workspace.py` - Save/load project state

### UI Components
- `src/opendata/ui/components/chat.py` - Chat, status modal
- `src/opendata/ui/components/files_dialog.py` - File selection
- `src/opendata/ui/context.py` - AppContext, refreshable registration
- `src/opendata/ui/state.py` - ScanState, UIState

---

## 🚀 Release Checklist

### Pre-Release
- [ ] Run `pytest` - all tests must pass
- [ ] Check working tree is clean
- [ ] Verify no uncommitted debugging code

### Release Steps
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

### Post-Release
- [ ] Verify website updated: `curl https://jochym.github.io/opendata/ | grep "v0.22"`
- [ ] Verify release assets: `gh release view v0.22.40 --json assets`
- [ ] Delete feature branch: `git branch -d fix/branch && git push origin --delete fix/branch`
- [ ] Clean working tree: `git status` should show clean

---

## 💡 Universal Debugging Principles

### 1. Verify Assumptions Immediately
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

### 2. Isolate the Problem Layer
```
User sees issue → UI layer? → Check browser (agent-browser)
                          ↓
                    State layer? → Check ctx.session, ScanState
                          ↓
                 Persistence layer? → Check JSON files, database
                          ↓
                   Model layer? → Test model_validate_json directly
```

### 3. Use the Right Tool for the Job
- **UI issues**: `agent-browser` + snapshots
- **State issues**: Add logging, check `ctx.refresh()` calls
- **Persistence issues**: `cat <file>.json`, test model loading
- **Performance issues**: `ps aux`, check loop operations

### 4. One Change at a Time
- Make ONE fix
- Test immediately
- Verify it works
- THEN move to next fix

**Never** make 5 changes then test - you won't know which one fixed/broke it.

### 5. Document as You Go
- When you find a bug, note the symptom and root cause
- When you fix it, note the pattern for future reference
- Add to this handoff document after the session

---

## 🎯 Next Session Starter Checklist

```bash
# 1. Clean environment
git checkout main
git pull origin main
git status  # Should be clean

# 2. Check issues
gh issue list

# 3. Pick issue and create branch
git checkout -b fix/issue-<number>

# 4. Set up test environment
pkill -9 -f "python src/opendata/main.py"
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python src/opendata/main.py --host 127.0.0.1 --port 8891 --no-browser --headless &
sleep 5
curl -I http://127.0.0.1:8891  # Verify it's running

# 5. Reproduce the bug (document steps)
# 6. Write test that fails
# 7. Implement fix
# 8. Verify test passes
# 9. Clean up and commit

# 10. Before finishing
pytest  # All tests must pass
pkill -f "python src/opendata/main.py"  # Clean up test process
```

---

**Last Updated**: v0.22.39 (2026-03-04)  
**Maintainer**: Add new lessons after each session

---

## 📝 Bug Fix Log: Issue #37 - Chat Instruction Disappears

### Problem
The welcome instruction in the chat window disappeared after the first interaction (e.g., after clicking Scan or AI Analyze). User expected it to stay until explicitly dismissed.

### Root Cause
1. **SessionState.reset()** was clearing ALL session state including `last_chat_len`, which is used for chat scroll positioning
2. The welcome message visibility logic checked `if not ctx.agent.chat_history`, which became False after the first system message was added
3. **No explicit dismiss mechanism** - welcome message should persist until user clicks a dismiss button

### Solution
**Three-part fix:**

1. **Add `welcome_dismissed` flag to SessionState** (`src/opendata/ui/context.py:38`):
   ```python
   welcome_dismissed: bool = False
   ```

2. **Add dismiss button and update visibility logic** (`src/opendata/ui/components/chat.py:37-72`):
   - Welcome card now has an **X button** in top-right corner
   - Visibility controlled by `ctx.session.welcome_dismissed` flag
   - Stays visible across all interactions until explicitly dismissed
   - Resets when loading a new project (via `session.reset()`)

3. **Add `dismiss_welcome()` handler** (`src/opendata/ui/components/chat.py:564-568`):
   ```python
   async def dismiss_welcome(ctx: AppContext):
       """Dismiss the welcome message until next project load."""
       ctx.session.welcome_dismissed = True
       ctx.refresh("chat")
   ```

4. **Preserve `last_chat_len` during session reset** (`src/opendata/ui/context.py:40-49`):
   - Maintains chat scroll position across project loads

### Test Coverage
Created `tests/unit/ui/test_chat_welcome_persistence.py` with 7 tests:
- `test_welcome_shown_by_default`
- `test_welcome_stays_after_scan`
- `test_welcome_dismissed_by_user`
- `test_welcome_stays_with_user_messages`
- `test_session_reset_preserves_chat_len`
- `test_session_reset_with_zero_chat_len`
- `test_session_reset_clears_welcome_dismissed`

### Verification
```bash
pytest tests/unit/ui/test_chat_welcome_persistence.py -xvs  # 7 passed
pytest tests/ -x  # 175 passed, no regressions
```
