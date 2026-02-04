# AI Interface Refactoring Plan

This document outlines the refactoring of the AI interface to support multiple providers (Google Gemini and OpenAI-compatible APIs like Ollama or CLIProxyAPI).

## 1. Objectives
- Enable support for different AI engines while keeping Google Gemini as the default.
- Support local models (Ollama, LocalAI) via OpenAI-compatible endpoints.
- Allow frictionless switching between providers in the UI.
- Maintain shared utilities (arXiv, DOI, ORCID fetching) across all providers.

## 2. Changes Implemented

### Data Models (`src/opendata/models.py`)
Updated `UserSettings` to include:
- `ai_provider`: Literal["google", "openai"]
- `openai_api_key`: For OpenAI or authenticated local instances.
- `openai_base_url`: Endpoint for OpenAI-compatible APIs (default: `https://api.openai.com/v1`).
- `openai_model`: Default model to use for the OpenAI provider.

### Modular AI Architecture (`src/opendata/ai/`)
The AI logic was split into several files to separate concerns:
- **`base.py`**: Contains `BaseAIService` (ABC) and shared metadata fetching tools.
- **`google_provider.py`**: Handles Google Generative AI SDK and OAuth2 flows.
- **`openai_provider.py`**: Uses `requests` to interact with any OpenAI-compatible `/chat/completions` endpoint.
- **`service.py`**: Acts as a **Facade**. It holds the active provider and delegates all calls to it. Supports `reload_provider(settings)` for live switching.

### UI Enhancements (`src/opendata/ui/app.py`)
- **Setup Wizard**: Replaced the single "Sign in with Google" button with a tabbed interface.
    - **Google Tab**: Original OAuth2 flow.
    - **OpenAI/Local Tab**: Fields for API Key, Base URL, and Model Name.
- **Header**: The model selector now dynamically queries the active provider for available models via `list_available_models()`.
- **Hot-Reload**: Changing provider settings immediately re-initializes the AI service with the new configuration.

## 3. Usage for Local Models (Ollama)
To use with Ollama:
1. Ensure Ollama is running (`ollama serve`).
2. In the OpenData Tool Setup Wizard, go to **OpenAI / Ollama** tab.
3. Set **Base URL** to `http://localhost:11434/v1`.
4. Set **Model Name** to your desired local model (e.g., `llama3`).
5. Click **Save & Connect**.

## 4. Search Grounding Note
While Google Gemini has built-in `google_search` grounding, other providers currently rely on the heuristic extractors and external tools (arXiv/DOI/ORCID) provided in the `BaseAIService`.
