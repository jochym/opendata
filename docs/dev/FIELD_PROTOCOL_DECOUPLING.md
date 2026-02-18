# Field Protocol Decoupling - Bug Fix

**Date:** February 17, 2026  
**Issue:** Field protocol selection was incorrectly coupled with RODBUK metadata classification fields

---

## Problem

### Root Cause
The code was reading/writing field protocol selection from/to `metadata.science_branches_mnisw`, which is a **RODBUK repository classification field**, not a tool configuration field.

**Impact:**
- User's field protocol selection got mixed with RODBUK metadata
- Changing RODBUK classification could change tool behavior (exclusions)
- Field protocol wasn't persisting correctly
- i18n/translation issues with field names

### Broken Flow
```
User selects "Physics" protocol in UI
    ↓
Code writes to metadata.science_branches_mnisw = ["physics"]  ❌ WRONG PLACE
    ↓
RODBUK classification field now controls tool behavior
    ↓
User changes RODBUK classification → tool exclusions change unexpectedly
```

---

## Solution

### Architecture Fix
**Separate concerns:**
- **Field Protocol** → `project_config.json` (tool configuration, user-selectable)
- **RODBUK Classification** → `metadata.yaml` (repository metadata, required for submission)

### Correct Flow
```
User selects "Physics" protocol in UI
    ↓
Code writes to project_config.json: {"field_name": "physics"}  ✅ CORRECT
    ↓
Tool uses field protocol for exclusions/prompts
    ↓
User separately fills RODBUK classification in metadata
    ↓
Two independent systems - no interference
```

---

## Changes Made

### 1. WorkspaceManager (`src/opendata/workspace.py`)
**Added:**
```python
def get_project_config_path(self, project_id: str) -> Path:
    """Returns the path to the project's config file."""
    return self.get_project_dir(project_id) / "project_config.json"

def load_project_config(self, project_id: str) -> Dict[str, Any]:
    """Loads project-specific configuration (field protocol, UI preferences, etc.)."""
    config_path = self.get_project_config_path(project_id)
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_project_config(self, project_id: str, config: Dict[str, Any]):
    """Saves project-specific configuration."""
    config_path = self.get_project_config_path(project_id)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
```

### 2. ProjectAnalysisAgent (`src/opendata/agents/project_agent.py`)
**Changed `_get_effective_field()`:**
```python
# BEFORE: Read from metadata
if self.current_metadata.science_branches_mnisw:
    return self.current_metadata.science_branches_mnisw[0]

# AFTER: Read from project config
if self.project_id:
    config = self.wm.load_project_config(self.project_id)
    if config.get("field_name"):
        return config["field_name"]
```

**Added `set_field_protocol()`:**
```python
def set_field_protocol(self, field_name: str):
    """User explicitly selects a field protocol."""
    if self.project_id:
        config = self.wm.load_project_config(self.project_id)
        config["field_name"] = field_name
        self.wm.save_project_config(self.project_id, config)
```

**Removed metadata clobbering:**
```python
# REMOVED THIS CODE:
# if field_name and not self.current_metadata.science_branches_mnisw:
#     self.current_metadata.science_branches_mnisw = [field_name]
```

### 3. UI Components
**`inventory_logic.py`:**
```python
# BEFORE
field_name = None
if ctx.agent.current_metadata.science_branches_mnisw:
    field_name = ctx.agent.current_metadata.science_branches_mnisw[0].lower().replace(" ", "_")

# AFTER
field_name = ctx.agent._get_effective_field()  # Reads from project config
```

**`preview.py`:** Same change as `inventory_logic.py`

**`protocols.py`:**
```python
def on_field_changed(e):
    """User selected a new field protocol - save to project config."""
    if ctx.agent.project_id and e.value:
        ctx.agent.set_field_protocol(e.value)  # Save to project_config.json
        ctx.refresh("inventory")  # Refresh with new exclusions

field_select.on("update:model-value", on_field_changed)
```

---

## Testing

### Manual Test Steps
1. **Launch app:** `python src/opendata/main.py`
2. **Open project:** `/home/jochym/calc/3C-SiC/Project`
3. **Go to Protocols tab → Field**
4. **Select "physics" from dropdown**
5. **Check:** `cat ~/.opendata_tool/projects/{id}/project_config.json`
   - Should show: `{"field_name": "physics"}`
6. **Check metadata:** `cat ~/.opendata_tool/projects/{id}/metadata.yaml | grep science`
   - Should be **unchanged** (independent of field protocol)
7. **Change RODBUK classification** in metadata
   - Field protocol should **not change**
8. **Change field protocol** in UI
   - RODBUK classification should **not change**

### Expected Behavior
- ✅ Field protocol selector in Protocols tab works independently
- ✅ `project_config.json` stores field selection
- ✅ `metadata.yaml` science_branches fields are separate
- ✅ Changing one doesn't affect the other
- ✅ Protocol exclusions update when field protocol changes
- ✅ Heuristic detection still works as fallback (if no user selection)

---

## Migration Notes

### Existing Projects
Projects already have `project_config.json` with `field_name` field - **no migration needed**.

### Backward Compatibility
- If `project_config.json` doesn't exist or `field_name` is missing:
  - Agent falls back to heuristic detection (based on file extensions)
  - No breaking changes

### Data Integrity
- `metadata.science_branches_mnisw` and `metadata.science_branches_oecd` are now **purely for RODBUK submission**
- User can fill these independently of tool's field protocol
- No automatic syncing between field protocol and RODBUK classification

---

## Benefits

1. **Clean Separation:** Tool configuration vs repository metadata
2. **User Control:** Explicit field protocol selection, persists correctly
3. **No i18n Issues:** Field protocol IDs are stable (not translated)
4. **Flexibility:** Can use any field protocol regardless of RODBUK classification
5. **Backward Compatible:** Graceful fallback to heuristics

---

## Files Modified

- `src/opendata/workspace.py` (+3 methods)
- `src/opendata/agents/project_agent.py` (modified 2 methods, removed 1 coupling)
- `src/opendata/ui/components/inventory_logic.py` (simplified)
- `src/opendata/ui/components/preview.py` (simplified)
- `src/opendata/ui/components/protocols.py` (added save handler)

**Total:** 5 files, ~100 lines changed

---

## Next Steps

1. ✅ Test field protocol selection in UI
2. ✅ Verify `project_config.json` is updated correctly
3. ✅ Verify metadata is NOT affected by field protocol changes
4. ✅ Test heuristic fallback (when no user selection)
5. Document for users: "How to select field protocol"
