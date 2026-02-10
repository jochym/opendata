# Code Review Report: OpenData Tool (v0.12.0)

**Date:** 2026-02-10
**Reviewer:** Antigravity (AI Agent)
**Target Branch/Version:** v0.12.0
**Working Directory:** `/home/jochym/Projects/OpenData`

## 1. Executive Summary
The project is in a healthy, mature state. The architecture (NiceGUI + Pydantic + Modular Agents) is well-suited for the problem domain. The codebase demonstrates a clear separation of concerns, robust state management, and a user-friendly asynchronous UI.

However, the core agent logic (`ProjectAnalysisAgent`) is becoming a "God Object," and the UI components, while modular, contain some deeply nested layout definitions that could be simplified.

## 2. Detailed Findings

### A. Code Quality & Consistency
*   **Pydantic Usage:** Excellent usage of Pydantic V2 (`model_dump`, `field_validator`). The `Metadata` model acts as a strong "Source of Truth".
    *   *Minor Note:* `src/opendata/extractors/base.py` defines `PartialMetadata` manually. While this decouples extractors from the main model (good), ensure it stays in sync with `Metadata` fields.
*   **Typing Standards:** The codebase currently mixes legacy typing (`typing.List`, `typing.Dict`) with modern generic aliases (`list`, `dict`). Since `pyproject.toml` targets `py310`, you can safely standardize on the modern syntax.
    *   *Example:* `List[str]` -> `list[str]`, `Optional[str]` -> `str | None`.
*   **Logging vs. Print:** `src/opendata/agents/project_agent.py` uses `print(f"[ERROR] ...")` in catch blocks (e.g., line 176). This bypasses the standard logging configuration and might be missed in production logs.

### B. Architecture & Modularity
*   **Agent Complexity:** `ProjectAnalysisAgent` (850 lines) is handling:
    1.  State persistence (Save/Load)
    2.  File scanning & fingerprinting
    3.  Heuristic extraction coordination
    4.  AI Chat Loop & Tool execution
    *   *Risk:* This class is becoming difficult to test and maintain.
*   **UI Component Depth:** `src/opendata/ui/components/chat.py` -> `render_analysis_dashboard` contains deeply nested context managers (`with ui.splitter... with ui.column... with ui.card...`).
    *   *Improvement:* Extract the "Left Panel" (Chat) and "Right Panel" (Metadata) into separate functional components (`render_chat_panel(ctx)`, `render_metadata_panel(ctx)`).

### C. Error Handling & Stability
*   **Resilience:** The UI correctly wraps async calls in `try/except` blocks to prevent crashing the main event loop.
*   **Cancellation:** The use of `threading.Event` (`ScanState.stop_event`) is a robust pattern for cancelling long-running background tasks (scanning/AI).
*   **Inventory Refresh:** In `project_agent.py` line 170, the SQLite update is wrapped in a broad `try...except Exception`. While this prevents a crash, ensure that a corrupted DB doesn't silently leave the user with stale data.

### D. Technical Debt
*   **Legacy Comments:** `project_agent.py` line 769 mentions `# Legacy prompts`. If these are truly legacy, a ticket should be created to deprecate or remove them to keep the prompt logic clean.
*   **Hardcoded Values:**
    *   `src/opendata/models.py`: Default language is hardcoded to `["English"]`. This should likely be localized or configurable.
    *   `splitter_value`: Default `70.0`.

## 3. Specific Recommendations

### High Priority (Refactoring)
1.  **Decompose `ProjectAnalysisAgent`:**
    *   Move `refresh_inventory` and `scan_project_lazy` logic into a dedicated `ScannerService` or `InventoryManager`.
    *   Move `load_project`/`save_state` into a `ProjectStateManager` (or enhance `WorkspaceManager`).
    *   Keep `ProjectAnalysisAgent` focused purely on the AI interaction loop.

2.  **Modernize Type Hints:**
    *   Run a global find-replace or use `pyupgrade` to switch to Python 3.10+ type hinting syntax for cleaner code.

### Medium Priority (Cleanup)
3.  **UI Refactor:**
    *   In `chat.py`, break `render_analysis_dashboard` into:
        ```python
        def render_analysis_dashboard(ctx):
             with ui.splitter(...) as splitter:
                 with splitter.before:
                     render_chat_panel(ctx)
                 with splitter.after:
                     render_metadata_panel(ctx)
        ```

4.  **Logging Standardization:**
    *   Replace all `print(f"[ERROR]...")` with `logger.error(..., exc_info=True)` to ensure stack traces are captured.

### Low Priority (Feature/Polish)
5.  **Configurable Defaults:**
    *   Move hardcoded defaults (like "English") to a configuration file or the `i18n` module to better support the PL/EN requirement.

## 4. Conclusion
The codebase is high-quality and follows modern Python standards. The primary area for improvement is architectural decomposition of the main Agent class to prevent it from becoming unmanageable as features grow. The error handling is defensive and appropriate for a user-facing desktop application.
