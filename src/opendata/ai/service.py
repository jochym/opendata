from google import genai
import os
from pathlib import Path
from typing import Optional


class AIService:
    """Service to handle AI interactions without forcing manual API keys."""

    def __init__(self, provider: str = "google"):
        self.provider = provider
        self.client = None
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def extract_metadata(self, content: str) -> str:
        """Extracts metadata using the best available frictionless method."""
        if not self.client:
            return "AI provider not configured."

        response = self.client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"Extract research metadata from this content and return YAML:\n\n{content}",
        )
        return response.text

    def authenticate_interactive(self, ui_handler):
        """Triggers a browser-based OAuth2 flow."""
        # The ui_handler would be a NiceGUI component or callback
        # to show the login prompt and handle the redirect.
        pass
