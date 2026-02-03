import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google.generativeai as genai


def debug_auth():
    # 1. Define required scopes
    # We include both the functional scope and the quota scope
    SCOPES = [
        "https://www.googleapis.com/auth/generative-language",
        "https://www.googleapis.com/auth/generative-language.peruserquota",
    ]

    secrets_path = Path("/home/jochym/.opendata_tool/client_secrets.json")
    token_path = Path("debug_token.json")

    print(f"--- 1. Locating Secrets ---")
    if not secrets_path.exists():
        print(f"ERROR: client_secrets.json not found at {secrets_path}")
        return
    print(f"SUCCESS: Found secrets at {secrets_path}")

    # 2. Run OAuth2 Flow
    print(f"\n--- 2. Starting OAuth2 Flow ---")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
        # In a headless environment (remotely), run_local_server might fail
        # if it can't open a browser. We use port=0 to get a random free port.
        # We explicitly set open_browser=False to see the URL in the terminal.
        creds = flow.run_local_server(
            port=0,
            open_browser=False,
            success_message="Auth successful! You can close this tab.",
        )
        print(f"SUCCESS: Credentials obtained.")
        print(f"Granted Scopes: {creds.scopes}")
    except Exception as e:
        print(f"ERROR: OAuth flow failed: {e}")
        return

    # 3. Configure Gemini
    print(f"\n--- 3. Configuring Gemini SDK ---")
    try:
        # Use credentials directly, NOT api_key
        genai.configure(credentials=creds)
        model = genai.GenerativeModel("gemini-1.5-flash")
        print(f"SUCCESS: Model initialized.")
    except Exception as e:
        print(f"ERROR: Model initialization failed: {e}")
        return

    # 4. Test API Call
    print(f"\n--- 4. Testing API Call ---")
    try:
        response = model.generate_content("Hello! Are you there?")
        print(f"SUCCESS: Response received from Gemini:")
        print(f"---")
        print(response.text)
        print(f"---")
    except Exception as e:
        print(f"ERROR: API call failed.")
        print(f"Message: {e}")
        # If it is a 403, we need to know why
        if hasattr(e, "reason"):
            print(f"Reason: {e.reason}")


if __name__ == "__main__":
    debug_auth()
