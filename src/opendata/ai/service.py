from pathlib import Path
from typing import Optional, Callable
from opendata.models import UserSettings
from .base import BaseAIService
from .google_provider import GoogleProvider
from .openai_provider import OpenAIProvider


class AIService:
    """
    Facade for AI Providers.
    Delegates calls to the active provider (Google or OpenAI).
    """

    def __init__(self, workspace_path: Path, settings: UserSettings = None):
        self.workspace_path = workspace_path
        # If no settings provided, try to load defaults (though usually passed from UI)
        # For backward compatibility with existing tests that might just pass path
        if settings is None:
            # Create default settings (which defaults to Google)
            settings = UserSettings()

        self.settings = settings
        self.provider: BaseAIService = self._create_provider()

    def _create_provider(self) -> BaseAIService:
        if self.settings.ai_provider == "openai":
            return OpenAIProvider(self.workspace_path, self.settings)
        else:
            return GoogleProvider(self.workspace_path)

    def reload_provider(self, settings: UserSettings):
        """Hot-swaps the provider based on new settings."""
        self.settings = settings
        self.provider = self._create_provider()

    # --- Delegation Methods ---

    @property
    def model_name(self) -> str:
        return self.provider.model_name

    @model_name.setter
    def model_name(self, value: str):
        # Allow setting model name directly (used in UI)
        self.provider.switch_model(value)

    def authenticate(self, silent: bool = False) -> bool:
        return self.provider.authenticate(silent)

    def is_authenticated(self) -> bool:
        return self.provider.is_authenticated()

    def logout(self):
        self.provider.logout()

    def get_user_info(self) -> dict:
        return self.provider.get_user_info()

    def list_available_models(self) -> list[str]:
        return self.provider.list_available_models()

    def switch_model(self, name: str):
        self.provider.switch_model(name)

    def ask_agent(
        self, prompt: str, on_status: Optional[Callable[[str], None]] = None
    ) -> str:
        return self.provider.ask_agent(prompt, on_status=on_status)

    # --- Tool Wrappers (Delegated to Base/Provider) ---

    def fetch_arxiv_metadata(self, arxiv_id: str) -> str:
        return self.provider.fetch_arxiv_metadata(arxiv_id)

    def fetch_doi_metadata(self, doi: str) -> dict:
        return self.provider.fetch_doi_metadata(doi)

    def fetch_orcid_metadata(self, orcid: str) -> dict:
        return self.provider.fetch_orcid_metadata(orcid)

    def search_orcid_by_name(self, name: str) -> list:
        return self.provider.search_orcid_by_name(name)
