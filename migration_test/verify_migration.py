import os
import sys
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google import genai

# --- Configuration ---
# Mimic the scopes from the current codebase
SCOPES = [
    "https://www.googleapis.com/auth/generative-language.retriever",
    "https://www.googleapis.com/auth/generative-language.peruserquota",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Path to token file (assuming it's in the current directory or workspace)
TOKEN_PATH = Path("token.json")
CLIENT_SECRETS_PATH = Path.home() / ".opendata_tool" / "client_secrets.json"
if not CLIENT_SECRETS_PATH.exists():
    CLIENT_SECRETS_PATH = Path("client_secrets.json")


def get_credentials():
    creds = None
    if TOKEN_PATH.exists():
        print(f"Loading credentials from {TOKEN_PATH}...")
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception as e:
            print(f"Error loading token: {e}")
            creds = None

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing credentials...")
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"Error refreshing token: {e}")
            creds = None

    if not creds or not creds.valid:
        print("No valid credentials found. Starting login flow...")
        if not CLIENT_SECRETS_PATH.exists():
            print(
                f"Error: {CLIENT_SECRETS_PATH} not found. Please provide client secrets."
            )
            return None

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_PATH), SCOPES
            )
            # Try to run local server first
            print("Attempting to launch browser for authentication...")
            try:
                creds = flow.run_local_server(port=0, open_browser=True)
            except Exception:
                print("Browser launch failed. Please open the following URL manually:")
                # If run_local_server fails, we might need run_console for remote envs
                # But run_local_server with open_browser=False still needs a callback.
                # Let's try run_console which is more robust for copy-paste flows.
                print("Switching to console flow...")
                creds = flow.run_console()

            # Save the credentials for the next run
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
            print(f"Saved new credentials to {TOKEN_PATH}")
        except Exception as e:
            print(f"Login failed: {e}")
            return None

    return creds


def verify_genai_client(creds):
    print("\n--- Verifying google-genai Client ---")
    model_id = "gemini-2.0-flash"

    try:
        print("Attempting to initialize Client with credentials...")
        client = genai.Client(credentials=creds)

        print(f"Generating content with {model_id}...")
        response = client.models.generate_content(
            model=model_id,
            contents="Hello, confirm you are working with OAuth credentials.",
        )

        print("\nSUCCESS! Response received:")
        print(response.text)
        return True

    except Exception as e:
        print(f"\nFAILURE with standard init: {e}")

        print("\nAttempting workaround: Injecting Authorization header...")
        try:
            # Refresh to ensure we have a valid token string
            if creds.expired:
                creds.refresh(Request())

            token = creds.token
            headers = {"Authorization": f"Bearer {token}"}
            if hasattr(creds, "quota_project_id") and creds.quota_project_id:
                headers["X-Goog-User-Project"] = str(creds.quota_project_id)

            client = genai.Client(http_options={"headers": headers})

            response = client.models.generate_content(
                model=model_id,
                contents="Hello, confirm you are working with injected headers.",
            )
            print("\nSUCCESS with workaround! Response received:")
            print(response.text)
            return True

        except Exception as e2:
            print(f"\nFAILURE with workaround: {e2}")
            return False


if __name__ == "__main__":
    print("Starting Migration Verification...")
    creds = get_credentials()
    if creds:
        verify_genai_client(creds)
    else:
        print("Could not obtain credentials.")
