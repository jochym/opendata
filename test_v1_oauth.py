import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google.generativeai as genai


# Test script for v1 library with OAuth2
def test_v1_hello():
    # Updated scopes based on user console availability
    SCOPES = [
        "https://www.googleapis.com/auth/generative-language.retriever",
        "https://www.googleapis.com/auth/generative-language.peruserquota",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    secrets_path = Path("/home/jochym/.opendata_tool/client_secrets.json")
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
            # Use console flow for simplicity
            creds = flow.run_local_server(port=0, open_browser=False)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    # 2. Configure v1 SDK
    try:
        print("\nInitializing google-generativeai (v1) with credentials...")
        genai.configure(credentials=creds)

        print("Listing available models...")
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(f"  - {m.name}")

        # The list showed several models. gemini-1.5-flash was missing.
        # Let's try gemini-flash-latest or one of the lite versions.
        model_name = "gemini-flash-latest"
        print(f"\nAttempting to use: {model_name}")
        model = genai.GenerativeModel(model_name)

        print("Sending simple Hello...")
        response = model.generate_content("Say 'OpenData v1 working'")

        print("\n--- RESPONSE ---")
        print(response.text)
        print("----------------")

    except Exception as e:
        print(f"\nFAILED: {e}")


if __name__ == "__main__":
    test_v1_hello()
