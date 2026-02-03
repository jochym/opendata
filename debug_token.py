import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google.generativeai as genai


def test_existing_token():
    # Scopes we expect to have
    SCOPES = [
        "https://www.googleapis.com/auth/generative-language",
        "https://www.googleapis.com/auth/generative-language.peruserquota",
    ]

    token_path = Path("/home/jochym/.opendata_tool/workspaces/token.json")

    print(f"--- 1. Loading Existing Token ---")
    if not token_path.exists():
        print(f"ERROR: token.json not found at {token_path}")
        return

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        print(f"SUCCESS: Token loaded.")

        if not creds.valid:
            print("Token is invalid/expired. Attempting refresh...")
            creds.refresh(Request())
            print("SUCCESS: Token refreshed.")

        print(f"Granted Scopes: {creds.scopes}")
    except Exception as e:
        print(f"ERROR: Failed to load/refresh token: {e}")
        return

    # 2. Configure Gemini
    print(f"\n--- 2. Configuring Gemini SDK ---")
    try:
        genai.configure(credentials=creds)
        model = genai.GenerativeModel("gemini-1.5-flash")
        print(f"SUCCESS: Model initialized.")
    except Exception as e:
        print(f"ERROR: Model initialization failed: {e}")
        return

    # 3. Test API Call
    print(f"\n--- 3. Testing API Call ---")
    try:
        response = model.generate_content("Hello from the debug script!")
        print(f"SUCCESS: Response received from Gemini:")
        print(f"---")
        print(response.text)
        print(f"---")
    except Exception as e:
        print(f"ERROR: API call failed.")
        print(f"Message: {e}")


if __name__ == "__main__":
    test_existing_token()
