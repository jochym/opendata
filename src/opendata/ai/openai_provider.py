import requests
from pathlib import Path
from typing import Optional, Callable
from .base import BaseAIService
from opendata.models import UserSettings


class OpenAIProvider(BaseAIService):
    """
    Generic OpenAI-compatible provider.
    Works with OpenAI API, Ollama, LocalAI, etc.
    """

    def __init__(self, workspace_path: Path, settings: UserSettings):
        super().__init__(workspace_path)
        self.settings = settings
        self.api_key = (
            settings.openai_api_key or "dummy-key"
        )  # Ollama often ignores key, but some need it
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model_name = settings.openai_model

    def authenticate(self, silent: bool = False) -> bool:
        # OpenAI/Local style auth is stateless (key based), so we just check if we can reach the API
        if silent:
            # In silent mode, we assume if we have config, we are "ready"
            return bool(self.base_url)

        try:
            # Simple check call (list models)
            self.list_available_models()
            return True
        except Exception:
            return False

    def is_authenticated(self) -> bool:
        return bool(self.base_url)

    def logout(self):
        # Nothing to clear for API key based auth (settings are managed by WorkspaceManager)
        pass

    def get_user_info(self) -> dict:
        return {"provider": "OpenAI / Compatible", "account": self.base_url}

    def list_available_models(self) -> list[str]:
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                # Handle standard OpenAI response format {"data": [{"id": "..."}]}
                if "data" in data:
                    return [m["id"] for m in data["data"]]
                return [self.model_name]  # Fallback
            else:
                return [self.model_name]
        except Exception:
            return [self.model_name]

    def switch_model(self, name: str):
        self.model_name = name
        # We should ideally update settings here, but this class is transient?
        # The parent Service or UI handles settings persistence.
        # Here we just update internal state.

    def ask_agent(
        self, prompt: str, on_status: Optional[Callable[[str], None]] = None
    ) -> str:
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }

            response = requests.post(url, json=payload, headers=headers, timeout=60)

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content
            else:
                return f"AI Error ({response.status_code}): {response.text}"

        except Exception as e:
            return f"AI Connection Error: {e}"
