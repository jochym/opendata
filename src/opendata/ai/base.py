from abc import ABC, abstractmethod
from typing import List, Optional, Callable
import requests
from pathlib import Path


class BaseAIService(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.model_name = "default"

    @abstractmethod
    def authenticate(self, silent: bool = False) -> bool:
        """Authenticates with the provider."""
        pass

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Returns authentication status."""
        pass

    @abstractmethod
    def ask_agent(
        self, prompt: str, on_status: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Sends a prompt to the AI and returns the text response.

        Args:
            prompt: The input prompt.
            on_status: Optional callback to report status updates (e.g. rate limit retries).
        """
        pass

    @abstractmethod
    def list_available_models(self) -> List[str]:
        """Lists models available for this provider."""
        pass

    @abstractmethod
    def switch_model(self, name: str):
        """Switches the active model."""
        pass

    @abstractmethod
    def logout(self):
        """Logs out/clears credentials."""
        pass

    # --- Shared Tools (Provider Agnostic) ---

    def fetch_arxiv_metadata(self, arxiv_id: str) -> str:
        try:
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            response = requests.get(url, timeout=10)
            return response.text
        except Exception as e:
            return f"Error fetching arXiv: {e}"

    def fetch_doi_metadata(self, doi: str) -> dict:
        try:
            url = f"https://doi.org/{doi}"
            headers = {"Accept": "application/vnd.citationstyles.csl+json"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}

    def fetch_orcid_metadata(self, orcid: str) -> dict:
        try:
            url = f"https://pub.orcid.org/v3.0/{orcid}"
            headers = {"Accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}

    def search_orcid_by_name(self, name: str) -> list:
        try:
            url = "https://pub.orcid.org/v3.0/expanded-search/"
            params = {"q": name}
            headers = {"Accept": "application/json"}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            return (
                response.json().get("expanded-result", [])[:5]
                if response.status_code == 200
                else []
            )
        except Exception:
            return []
