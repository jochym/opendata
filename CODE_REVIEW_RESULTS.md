# Code Review Report - OpenData Tool
**Date:** 2026-02-22
**Status:** Action Required

## 1. Critical Bug: AI Response Parsing Logic
In `src/opendata/agents/parsing.py`, there is a logic error in how the `QUESTION:` section is handled, which will cause parsing failures when AI includes a question after the metadata block.

**File:** `src/opendata/agents/parsing.py`
```python
70:         if "QUESTION:" in after_metadata:
71:             json_section, question_section = after_metadata.split("QUESTION:", 1)
72:             clean_text = question_section.strip()
73:         else:
74:             json_section = after_metadata
75:             clean_text = ""
76: 
77:         json_section = after_metadata.strip() # BUG: Overwrites split result with full content
```
**Impact:** Line 77 effectively ignores the split performed in lines 70-75. If the AI responds with `METADATA: {...} QUESTION: Is this correct?`, the `json_section` will include the `QUESTION:` text, leading to `json.JSONDecodeError` or YAML parser errors.

---

## 2. Architecture & Correctness

### `src/opendata/agents/parsing.py` - Format Detection
The detection of JSON vs YAML (line 80) relies on a simple `startswith`.
```python
80:         is_json = json_section.startswith("{") or json_section.startswith("```json")
```
While usually safe with LLMs, YAML can technically start with `{` (flow style). A more robust approach would be attempting JSON parsing first, then falling back to YAML.

### `src/opendata/workspace.py` - Project Deletion
The `delete_project` method (lines 248-267) correctly handles file locking issues (especially on Windows) by using `gc.collect()` and manual retries. This is a good defensive practice for SQLite-backed applications.

---

## 3. Test Coverage & Completeness

*   **New YAML Tests:** `tests/unit/agents/test_parsing_yaml.py` correctly verifies the migration to YAML format.
*   **Realistic Tests:** `tests/unit/agents/test_parsing_realistic.py` provides good regression for complex normalization cases (authors, contacts).
*   **Missing Case:** There is no test case for the `QUESTION:` split bug identified above. A test should be added where metadata is followed by a question block.

---

## 4. Refactoring Suggestions

### `src/opendata/agents/parsing.py` - Normalization Bloat
The function `extract_metadata_from_ai_response` is exceeding 400 lines with repetitive `if "field" in updates: ...` blocks.
*   **Recommendation:** Move normalization logic (e.g., `normalize_authors`, `normalize_funding`) into separate helper functions or methods within the `Metadata` model.

### `src/opendata/ui/components/header.py` - State Management
In `handle_load_project` (line 126), `ctx.session = SessionState()` resets the entire UI session. Verify if any non-persisted UI preferences (like specific tab state or filters) should be preserved when switching projects.

---

## Summary of Action Items
1. **Fix line 77 in `src/opendata/agents/parsing.py`** to respect the `QUESTION:` split.
2. **Add a unit test** specifically covering the `METADATA: ... QUESTION: ...` scenario.
3. **Refactor normalization logic** to improve maintainability of the parsing module.
