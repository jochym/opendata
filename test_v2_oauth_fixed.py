import os
import json
from pathlib import Path
from google import genai
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# Proving script for v2 library with OAuth2
def test_v2_hello():
    # Proven scopes from v1 test
    SCOPES = [
        "https://www.googleapis.com/auth/generative-language.retriever",
        "https://www.googleapis.com/auth/generative-language.peruserquota",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    secrets_path = Path("/home/jochym/.opendata_tool/client_secrets.json")
    # Reuse the token from v1 test if it exists to save a login step
    token_path = Path("test_v1_token.json")

    print(f"Checking for secrets at: {secrets_path}")
    if not secrets_path.exists():
        print("Error: client_secrets.json not found")
        return

    # 1. Get Credentials
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0, open_browser=False)

        with open("test_v2_token.json", "w") as token:
            token.write(creds.to_json())

    # 2. Configure v2 SDK
    try:
        print("\nInitializing google-genai (v2) with credentials...")
        # Note: We are testing the official 'credentials' parameter
        client = genai.Client(credentials=creds)

        # Proven model name from v1 test
        model_name = "gemini-flash-latest"
        print(f"Sending simple Hello to {model_name}...")

        response = client.models.generate_content(
            model=model_name, contents="Say 'OpenData v2 working'"
        )

        print("\n--- RESPONSE ---")
        print(response.text)
        print("----------------")

    except Exception as e:
        print(f"\nFAILED: {e}")


if __name__ == "__main__":
    test_v2_hello()
