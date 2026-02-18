import os
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Callable, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google import genai

from .base import BaseAIService
from .telemetry import AITelemetry
from opendata.utils import get_resource_path

logger = logging.getLogger("opendata.ai.genai_provider")


class GenAIProvider(BaseAIService):
    """
    Modern Google GenAI Provider using the google-genai SDK.
    Includes telemetry and response ID injection.
    """

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
        self.client = None
        self.model_name = ""  # Empty initially, will be set after auth
        self._auth_lock = threading.Lock()

        # Initialize telemetry
        log_path = workspace_path / "logs" / "ai_interactions.jsonl"
        # Force parent directory creation before AITelemetry init
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.telemetry = AITelemetry(log_path)

    def logout(self):
        if self.token_path.exists():
            self.token_path.unlink()
        self.creds = None
        self.client = None

    def get_user_info(self) -> dict:
        info = {"provider": "Google GenAI (Modern)", "account": "Not signed in"}
        if self.creds:
            from googleapiclient.discovery import build

            try:
                service = build("oauth2", "v2", credentials=self.creds)
                user_info = service.userinfo().get().execute()
                info["account"] = user_info.get("email", "Unknown")
            except Exception:
                info["account"] = "Signed in"
        return info

    def list_available_models(self) -> List[str]:
        if not self.client:
            return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        try:
            self._ensure_fresh_client()
            # The SDK models.list() returns an iterable of model objects
            models = self.client.models.list()  # type: ignore
            available = []
            for m in models:
                methods = getattr(m, "supported_generation_methods", None) or getattr(
                    m, "supported_actions", []
                )
                if "generateContent" in methods:
                    available.append(m.name.replace("models/", ""))  # type: ignore
            return (
                available
                if available
                else ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            )
        except Exception:
            return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

        try:
            self._ensure_fresh_client()
            return [
                m.name.replace("models/", "")  # type: ignore
                for m in self.client.models.list()  # type: ignore
                if "generateContent"
                in (getattr(m, "supported_generation_methods", None) or [])
            ]

        except Exception:
            return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

    def switch_model(self, name: str):
        self.model_name = name

    def is_authenticated(self) -> bool:
        return self.client is not None

    def _create_client(self):
        if not self.creds:
            return None

        token = self.creds.token
        headers = {
            "Authorization": f"Bearer {token}",
            "x-goog-api-key": "",
        }
        if hasattr(self.creds, "quota_project_id") and self.creds.quota_project_id:
            headers["X-Goog-User-Project"] = str(self.creds.quota_project_id)

        return genai.Client(
            api_key="dummy_key_to_bypass_sdk_check", http_options={"headers": headers}
        )

    def _ensure_fresh_client(self):
        if self.creds and self.creds.expired:
            with self._auth_lock:
                self.creds.refresh(Request())
                self.client = self._create_client()

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

                self.client = self._create_client()

                # Auto-detect best model after successful auth
                try:
                    available = self.list_available_models()
                    if available:
                        # Priority: 1. gemini-flash-latest, 2. gemini-3-flash-preview,
                        # 3. gemini-2.5-flash, 4. gemini-2.0-flash, 5. any flash, 6. any light, 7. first available
                        priority_list = [
                            "gemini-flash-latest",
                            "gemini-3-flash-preview",
                            "gemini-2.5-flash",
                            "gemini-2.0-flash",
                        ]

                        found_model = None
                        for target in priority_list:
                            if target in available:
                                found_model = target
                                break

                        if found_model:
                            self.model_name = found_model
                        else:
                            flash_models = [
                                m for m in available if "flash" in m.lower()
                            ]
                            if flash_models:
                                self.model_name = flash_models[0]
                            else:
                                light_models = [
                                    m for m in available if "light" in m.lower()
                                ]
                                if light_models:
                                    self.model_name = light_models[0]
                                else:
                                    self.model_name = available[0]
                except Exception:
                    self.model_name = "gemini-2.0-flash"  # Safe fallback

                return True

            return False

    def ask_agent(
        self, prompt: str, on_status: Optional[Callable[[str], None]] = None
    ) -> str:
        if not self.client:
            if not self.authenticate(silent=True):
                return "AI not authenticated."

        interaction_id = self.telemetry.generate_id()
        max_retries = 5
        wait_time = 2
        start_time = time.time()

        for attempt in range(max_retries):
            try:
                self._ensure_fresh_client()

                response = self.client.models.generate_content(  # type: ignore
                    model=self.model_name, contents=prompt
                )

                latency = (time.time() - start_time) * 1000
                response_text = response.text or ""

                # Log interaction
                self.telemetry.log_interaction(
                    interaction_id=interaction_id,
                    model_name=self.model_name,
                    prompt=prompt,
                    response=response_text,
                    latency_ms=latency,
                )

                # Inject ID tag
                return response_text + self.telemetry.get_id_tag(interaction_id)

            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    msg = f"⏳ Rate limit hit (429). Retrying in {wait_time}s..."
                    if on_status:
                        on_status(msg)
                    time.sleep(wait_time)
                    wait_time *= 2
                    continue

                error_msg = f"AI Error: {e}"
                self.telemetry.log_interaction(
                    interaction_id=interaction_id,
                    model_name=self.model_name,
                    prompt=prompt,
                    response=error_msg,
                    latency_ms=(time.time() - start_time) * 1000,
                    metadata={"error": str(e), "attempt": attempt + 1},
                )
                return error_msg

        return "AI Error: Rate limit exceeded."
