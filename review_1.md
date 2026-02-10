# Code Review Report: OpenData Tool

## 1. Executive Summary
The OpenData Tool is in a mature state for a local, browser-based application. The architecture successfully adheres to the "Stateless Model, Stateful Agent" principle, and the transition to Phase 19 has resulted in a well-structured, modular codebase. The strict read-only guarantee for user data is well-implemented and tested.

The application leverages modern Python features (Pydantic V2, Pathlib, Asyncio) effectively. Performance bottlenecks regarding large file trees have been addressed via `os.scandir` generators and SQLite caching. The primary area for improvement lies in the `ProjectAnalysisAgent` class, which is becoming a "God Object," and the reliance on static class attributes for UI state, which—while functional for a single-user desktop app—adds fragility to state resets.

## 2. Strengths

*   **Robust "Read-Only" Architecture:** The separation between the user's research directory (read-only) and the application's workspace (`~/.opendata_tool/`) is strictly enforced. `tests/test_safety.py` explicitly validates this boundary, ensuring research integrity.
*   **High-Performance Scanning:** The switch to `os.scandir` with generator-based traversal (`src/opendata/utils.py:walk_project_files`) allows the tool to handle projects with huge file counts without memory spikes. The integration of SQLite (`ProjectInventoryDB`) with WAL mode for caching file inventories is a professional touch.
*   **Modern Tech Stack Usage:**
    *   **NiceGUI:** effective use of async/await for non-blocking UI updates.
    *   **Pydantic V2:** strong schema validation for metadata and partial updates.
    *   **Pathlib:** consistent, cross-platform path handling throughout the codebase.
*   **Modular UI:** The refactoring of `src/opendata/ui/` into specific components (`chat.py`, `metadata.py`, `package.py`) drastically improves readability and maintainability compared to a monolithic `app.py`.
*   **Safety Features:** The implementation of a "Desktop Control Window" (kill switch) and strict localhost binding (127.0.0.1) by default demonstrates a strong security posture.

## 3. Issues & Concerns

### Architecture & Design
*   **Agent Class Cohesion:** `ProjectAnalysisAgent` (`src/opendata/agents/project_agent.py`) is ~850 lines long. It currently handles:
    1.  State persistence (loading/saving).
    2.  Chat history management.
    3.  Heuristic extraction orchestration.
    4.  Tool execution loops.
    5.  Metadata merging logic.
    *Refactoring Suggestion:* Move the "Tool Loop" and "Chat History" management into a `ConversationEngine` class, leaving `ProjectAnalysisAgent` to focus purely on high-level decision making.

*   **Global Mutable State:** `src/opendata/ui/state.py` relies heavily on static class attributes (`UIState.inventory_cache`, `UIState.folder_children_map`). While acceptable for a single-user local app, this pattern requires manual resetting of variables when switching projects (seen in `inventory_logic.py:126`). This is error-prone; if a developer forgets to reset a new flag, state bleeds between projects.

### Code Quality
*   **Manual I18n Instantiation:** The translation function `_()` relies on a global `_current_t` variable in `src/opendata/i18n/translator.py`. While it works, it makes unit testing independent modules harder if they rely on this global state being initialized.

### Error Handling
*   **Broad Exception Catching:** In `src/opendata/utils.py`, `read_file_header` catches generic `Exception` and returns an empty string. While this prevents crashes, it might mask permission errors or I/O failures that the user should be warned about (e.g., "File exists but is unreadable").

## 4. Recommendations

### Immediate Actions
1.  **Refactor `ProjectAnalysisAgent`:** Extract the tool execution loop (lines 393-611) into a dedicated `ToolExecutor` or `ChatLoop` class. This will make the core agent logic easier to test and modify.
2.  **Encapsulate UI State:** Instead of static attributes on `UIState`, instantiate a `SessionState` dataclass within `AppContext`. This allows state to be cleared automatically by simply creating a new instance when a project is loaded, removing the need for manual variable resetting.
3.  **Harden File Reading:** In `src/opendata/utils.py`, differentiate between `FileNotFoundError`/`PermissionError` (warn the user) and encoding errors (fallback/ignore) inside `read_file_header`.

### Long-Term Improvements
1.  **Dependency Injection for Agents:** Currently, `ProjectAnalysisAgent` instantiates its own `ExtractorRegistry`. Injecting this dependency would allow for easier testing with mock extractors.
2.  **Structured Logging:** While `logging` is used, the application could benefit from a structured log format (JSON) in the `~/.opendata_tool/logs/` directory to help with debugging the "stateless model" context window issues.

## 5. Security Check
*   **Read-Only:** **CONFIRMED.** No write operations detected targeting the `project_dir`. All writes are directed to `wm.get_project_dir()` (workspace).
*   **Network:** **SECURE.** `start_ui` binds to `127.0.0.1`. The implementation of `get_local_ip` is only used for the mobile QR code feature, which is user-initiated.
*   **Secrets:** **SAFE.** OAuth2 tokens are handled via Google's libraries. `settings.yaml` stores config but no hardcoded secrets were found in the source.
