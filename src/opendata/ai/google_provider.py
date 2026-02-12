import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
import threading
import time
import sys
import os
from typing import Optional, Callable
from .base import BaseAIService
from opendata.utils import get_resource_path


class GoogleProvider(BaseAIService):
    SCOPES = [
        "https://www.googleapis.com/auth/generative-language.retriever",
        "https://www.googleapis.com/auth/generative-language.peruserquota",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def __init__(self, workspace_path: Path):
        super().__init__(workspace_path)
        self.token_path = workspace_path / "token.json"
        self.creds = None
        self.model = None
        self.model_name = "gemini-flash-latest"
        self._auth_lock = threading.Lock()

    def logout(self):
        if self.token_path.exists():
            self.token_path.unlink()
        self.creds = None
        self.model = None

    def get_user_info(self) -> dict:
        info = {"provider": "Google Gemini", "account": "Not signed in"}
        if self.creds:
            # We can't easily get the email without an extra API call or if it's not in the token
            # But the scope "userinfo.email" is present, so we might have it if we use a helper
            # For now, let's look at what's in the creds
            from googleapiclient.discovery import build

            try:
                service = build("oauth2", "v2", credentials=self.creds)
                user_info = service.userinfo().get().execute()
                info["account"] = user_info.get("email", "Unknown")
            except Exception:
                info["account"] = "Signed in"
        return info

    def list_available_models(self) -> list[str]:
        if not self.creds:
            return []
        try:
            genai.configure(credentials=self.creds)
            return [
                m.name.replace("models/", "")
                for m in genai.list_models()
                if "generateContent" in m.supported_generation_methods
            ]
        except Exception:
            return ["gemini-flash-latest"]

    def switch_model(self, name: str):
        self.model_name = name
        if self.creds:
            genai.configure(credentials=self.creds)
            try:
                tools = [{"google_search": {}}] if "flash" in self.model_name else None
                self.model = genai.GenerativeModel(self.model_name, tools=tools)
            except Exception:
                self.model = genai.GenerativeModel(self.model_name)

    def is_authenticated(self) -> bool:
        return self.model is not None

    def authenticate(self, silent: bool = False) -> bool:
        with self._auth_lock:
            if self.token_path.exists():
                try:
                    self.creds = Credentials.from_authorized_user_file(
                        str(self.token_path), self.SCOPES
                    )
                except Exception:
                    self.creds = None

            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    self.creds = None

            if (not self.creds or not self.creds.valid) and not silent:
                client_id = os.environ.get("GOOGLE_CLIENT_ID")
                client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

                if client_id and client_secret:
                    # Construct client config from environment variables
                    client_config = {
                        "installed": {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                            "redirect_uris": ["http://localhost"],
                        }
                    }
                    try:
                        flow = InstalledAppFlow.from_client_config(
                            client_config, self.SCOPES
                        )
                        self.creds = flow.run_local_server(port=0, open_browser=True)
                    except Exception:
                        return False
                else:
                    # Try to find client_secrets.json in bundled resources or home dir
                    secrets_locations = [
                        get_resource_path("client_secrets.json"),
                        Path.home() / ".opendata_tool" / "client_secrets.json",
                        Path("client_secrets.json").absolute(),
                    ]

                    secrets_path = None
                    for loc in secrets_locations:
                        if loc.exists():
                            secrets_path = loc
                            break

                    if not secrets_path:
                        return False

                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            str(secrets_path), self.SCOPES
                        )
                        self.creds = flow.run_local_server(port=0, open_browser=True)
                    except Exception:
                        return False

            if self.creds and self.creds.valid:
                with open(self.token_path, "w") as token:
                    token.write(self.creds.to_json())
                genai.configure(credentials=self.creds)
                try:
                    tools = (
                        [{"google_search": {}}] if "flash" in self.model_name else None
                    )
                    self.model = genai.GenerativeModel(self.model_name, tools=tools)
                except Exception:
                    self.model = genai.GenerativeModel(self.model_name)
                return True
            return False

    def ask_agent(
        self, prompt: str, on_status: Optional[Callable[[str], None]] = None
    ) -> str:
        if not self.model:
            if not self.authenticate(silent=True):
                return "AI not authenticated."

        # Exponential Backoff for Rate Limits
        max_retries = 5
        wait_time = 2

        for attempt in range(max_retries):
            try:
                if self.creds and self.creds.expired:
                    with self._auth_lock:
                        self.creds.refresh(Request())
                        genai.configure(credentials=self.creds)

                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    msg = f"⏳ Rate limit hit (429). Retrying in {wait_time}s..."
                    if on_status:
                        on_status(msg)
                    time.sleep(wait_time)
                    wait_time *= 2  # Double the wait
                    continue
                return f"AI Error: {e}"

        return "AI Error: Rate limit exceeded (gave up after retries)."
