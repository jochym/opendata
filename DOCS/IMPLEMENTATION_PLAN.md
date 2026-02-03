# Implementation Plan: Persistence, Optimization, and Error Handling

## Plan 1: Project Manager and Persistence (Token-Optimized)
Goal: Save project state to disk and optimize AI context usage.
- **Unique Project ID:** MD5 hash of absolute project path.
- **State Persistence:** Save `metadata.yaml`, `chat_history.json`, and `fingerprint.json` to `~/.opendata_tool/projects/<project_id>/`.
- **Auto-save:** Trigger after every interaction turn.
- **Context Optimization:**
  - Summarize older history.
  - Compress fingerprints (send summaries instead of full lists).
  - Prioritize YAML metadata in prompts.
- **UI:** Support selecting and switching between projects.

## Plan 2: Prompt Factorization and Optimization
Goal: Move prompts to external files for easier tweaking.
- **Prompt Registry:** `src/opendata/prompts/`.
- **PromptManager:** Class to load and render Markdown templates.
- **Refactoring:** Update `ProjectAnalysisAgent` to use `PromptManager`.

## Plan 3: Error Handling and Rate Limit Monitoring
Goal: Resilience and transparency regarding API usage.
- **Robust Error Handling:** Introduce `AIQuotaExceededError`.
- **Usage Tracking:** Return and track token usage from `AIService`.
- **UI Feedback:** Display session token usage.
