import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
import json
import os
import threading
import requests
import time

class AIService:
    """Handles frictionless AI access via OAuth2 with Exponential Backoff."""

    SCOPES = [
        "https://www.googleapis.com/auth/generative-language.retriever",
        "https://www.googleapis.com/auth/generative-language.peruserquota",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email"
    ]

    def __init__(self, workspace_path: Path):
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

    def list_available_models(self) -> list[str]:
        if not self.creds: return []
        try:
            genai.configure(credentials=self.creds)
            return [m.name.replace('models/', '') for m in genai.list_models() 
                    if 'generateContent' in m.supported_generation_methods]
        except Exception: return ["gemini-flash-latest"]

    def switch_model(self, name: str):
        self.model_name = name
        if self.creds:
            genai.configure(credentials=self.creds)
            try:
                tools = [{'google_search': {}}] if 'flash' in self.model_name else None
                self.model = genai.GenerativeModel(self.model_name, tools=tools)
            except Exception:
                self.model = genai.GenerativeModel(self.model_name)

    def is_authenticated(self) -> bool:
        return self.model is not None

    def authenticate(self, silent: bool = False) -> bool:
        with self._auth_lock:
            if self.token_path.exists():
                try:
                    self.creds = Credentials.from_authorized_user_file(str(self.token_path), self.SCOPES)
                except Exception: self.creds = None

            if self.creds and self.creds.expired and self.creds.refresh_token:
                try: self.creds.refresh(Request())
                except Exception: self.creds = None

            if (not self.creds or not self.creds.valid) and not silent:
                home_secrets = Path.home() / ".opendata_tool" / "client_secrets.json"
                secrets_path = home_secrets if home_secrets.exists() else Path("client_secrets.json")
                if not secrets_path.exists(): return False
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), self.SCOPES)
                    self.creds = flow.run_local_server(port=0, open_browser=True)
                except Exception: return False

            if self.creds and self.creds.valid:
                with open(self.token_path, "w") as token:
                    token.write(self.creds.to_json())
                genai.configure(credentials=self.creds)
                try:
                    tools = [{'google_search': {}}] if 'flash' in self.model_name else None
                    self.model = genai.GenerativeModel(self.model_name, tools=tools)
                except Exception:
                    self.model = genai.GenerativeModel(self.model_name)
                return True
            return False

    def fetch_arxiv_metadata(self, arxiv_id: str) -> str:
        try:
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            response = requests.get(url, timeout=10)
            return response.text
        except Exception as e: return f"Error fetching arXiv: {e}"

    def fetch_doi_metadata(self, doi: str) -> dict:
        try:
            url = f"https://doi.org/{doi}"
            headers = {"Accept": "application/vnd.citationstyles.csl+json"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.json() if response.status_code == 200 else {}
        except Exception: return {}

    def fetch_orcid_metadata(self, orcid: str) -> dict:
        try:
            url = f"https://pub.orcid.org/v3.0/{orcid}"
            headers = {"Accept": "application/json"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.json() if response.status_code == 200 else {}
        except Exception: return {}

    def search_orcid_by_name(self, name: str) -> list:
        try:
            url = "https://pub.orcid.org/v3.0/expanded-search/"
            params = {"q": name}
            headers = {"Accept": "application/json"}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            return response.json().get("expanded-result", [])[:5] if response.status_code == 200 else []
        except Exception: return []

    def ask_agent(self, prompt: str) -> str:
        if not self.model:
            if not self.authenticate(silent=True): return "AI not authenticated."
        
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
                    time.sleep(wait_time)
                    wait_time *= 2 # Double the wait
                    continue
                return f"AI Error: {e}"
