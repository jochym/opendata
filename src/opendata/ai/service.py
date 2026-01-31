import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google import genai


class AIService:
    """Handles frictionless AI access via OAuth2/Google Account."""

    SCOPES = ["https://www.googleapis.com/auth/generative-language"]

    def __init__(self, workspace_path: Path):
        self.token_path = workspace_path / "token.json"
        self.creds = None
        self.client = None

    def authenticate(self) -> bool:
        """
        Attempts to load existing credentials or triggers OAuth2 flow.
        Checks current directory for client_secrets.json first (bundled mode).
        """
        if self.token_path.exists():
            self.creds = Credentials.from_authorized_user_file(
                str(self.token_path), self.SCOPES
            )

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                # Prioritize current directory for bundled client_secrets.json
                secrets_path = Path("client_secrets.json")
                if not secrets_path.exists():
                    # Fallback to hidden workspace
                    secrets_path = self.token_path.parent / "client_secrets.json"
                    if not secrets_path.exists():
                        return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(secrets_path), self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            # Save the credentials for next time
            with open(self.token_path, "w") as token:
                token.write(self.creds.to_json())

        if self.creds:
            # Note: The new google-genai SDK uses api_key or credentials
            # For now we use the credentials to initialize the client
            self.client = genai.Client(credentials=self.creds)
            return True

        return False

    def ask_agent(self, prompt: str) -> str:
        """Sends a structured prompt to Gemini."""
        if not self.client:
            return "AI not authenticated."

        response = self.client.models.generate_content(
            model="gemini-1.5-flash", contents=prompt
        )
        return response.text
