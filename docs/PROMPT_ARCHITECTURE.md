# Prompt Architecture and Mechanics in OpenData Tool

This document provides a detailed technical overview of how prompts are structured, managed, and executed within the OpenData Tool. It is intended for developers maintaining the system and advanced users wishing to customize the AI's behavior through protocols.

---

## 1. Core Philosophy: The "Stateless Agent"
The OpenData Tool treats the AI model as a stateless function. For every interaction, the system reconstructs the entire context from scratch. This ensures consistency and allows the AI to "see" the latest state of the metadata and project structure without relying on potentially stale chat history.

The context is built in a specific order:
`System Instructions` -> `Field Protocols` -> `Current Metadata (YAML)` -> `Project Fingerprint` -> `Recent History` -> `User Input`.

## 2. Hierarchical Protocol System
The "instructions" part of the prompt is a merge of four hierarchical layers. Later layers can supplement or refine the rules of earlier ones.

| Layer | Source | Purpose |
| :--- | :--- | :--- |
| **System** | Built-in (`protocols/manager.py`) | Core RODBUK schema rules and extraction logic. |
| **User** | `~/.opendata_tool/protocols/user.yaml` | Per-user preferences (e.g., "Always use ORCID"). |
| **Field** | `~/.opendata_tool/protocols/fields/*.yaml` | Domain knowledge (e.g., "In Physics, OUTCAR is VASP"). |
| **Project** | `[Project]/.opendata_tool/protocol.yaml` | Project-specific quirks and manual overrides. |

### Mechanics of Merging
When an analysis is triggered, the `ProtocolManager` resolves the "Effective Protocol":
1. It collects all `metadata_prompts` or `curator_prompts` from the active layers.
2. It deduplicates instructions while preserving the order (System -> User -> Field -> Project).
3. It merges `exclude_patterns` to guide the file scanner.

## 3. Context Injection Components
Every AI request is wrapped in a "Context Package" containing:

### A. Project Fingerprint
A lightweight summary of the directory:
*   Total file count and size.
*   Distribution of file extensions.
*   A sample of the file tree (first 50-100 files).
*   The identified "Primary Publication" (e.g., `main.tex`).

### B. Metadata Source of Truth (YAML)
The current draft of the RODBUK metadata is converted to YAML and injected. YAML is used because:
*   It is more token-efficient than JSON.
*   It is highly readable for the AI.
*   It clearly shows which fields are missing or populated.

### C. Heuristic Grounding
Before the AI is consulted, local "Heuristic Extractors" (Python-based) scan the files. Their findings (e.g., authors from LaTeX, software from OUTCAR) are placed in the prompt as "Gathered Heuristics" to prevent the AI from hallucinating details that are explicitly present in the files.

## 4. Agent Modes
The system operates in two distinct modes, each with its own System Prompt template.

### Metadata Mode (`system_prompt_metadata`)
**Goal:** Fill the RODBUK schema.
**Instructions:** 
*   Identify bibliographic details.
*   Map science branches (MNiSW/OECD).
*   Extract affiliations and funding.
*   Format output as a strict JSON block.

### Curator Mode (`system_prompt_curator`)
**Goal:** Ensure results reproducibility.
**Instructions:**
*   Analyze the relationship between data files and processing scripts.
*   Suggest specific files for inclusion in the final package.
*   Identify missing documentation (README, LICENSE).
*   Focus on "Data-Script Linkages".

## 5. Built-in System Prompts (Templates)

### The "Chat Wrapper"
All interactions are wrapped in this template to ensure the AI understands its role and the provided context:

```markdown
You are a scientific data curator helping a researcher prepare a project for the RODBUK repository.

[CONTEXT]
{{context}}

[CONVERSATION HISTORY]
{{history}}

[CURRENT USER INPUT]
{{user_input}}

Analyze the input and provide:
1. A helpful response to the user.
2. A METADATA: block containing a JSON update for the metadata if any new info was found.
```

### The Output Schema (JSON)
The AI is instructed to return updates in a structured format:

```json
{
  "ANALYSIS": {
    "summary": "Brief explanation of what was found",
    "missing_fields": ["list", "of", "missing", "keys"],
    "questions": [{"field": "key", "question": "text", "type": "text|choice"}]
  },
  "METADATA": {
    "title": "...",
    "authors": [{"name": "...", "identifier": "..."}]
  }
}
```

## 6. Prompt Mechanics for Developers
*   **PromptManager**: Located in `src/opendata/utils.py`, it uses Jinja2-style templates stored in the code or external files.
*   **Token Management**: The `AnalysisEngine` automatically prunes chat history to the last 15-20 messages to stay within context limits while keeping the full YAML metadata.
*   **Tool Use**: The system detects patterns like `arXiv:ID` or `DOI:...` in user input and triggers pre-prompt tools to fetch external data before the main AI call.

---
*Last updated: 2026-02-13*
