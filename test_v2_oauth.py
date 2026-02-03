import os
from pathlib import Path
from google import genai
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


# Minimal script to test google-genai (v2) with OAuth2
def test_v2():
    # 1. Define scopes
    # According to Google Cloud Console, peruserquota is needed for personal quota usage
    SCOPES = [
        "https://www.googleapis.com/auth/generative-language.peruserquota",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    secrets_path = Path("/home/jochym/.opendata_tool/client_secrets.json")
    token_path = Path("test_v2_token.json")

    print(f"Checking for secrets at: {secrets_path}")
    if not secrets_path.exists():
        print("Error: client_secrets.json not found")
        return

    # 2. Get Credentials
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            # Use console flow for simplicity in this minimal script
            creds = flow.run_local_server(port=0, open_browser=False)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    # 3. Initialize v2 Client
    # Official docs suggest passing credentials here
    try:
        print("\nInitializing google-genai (v2) Client...")
        client = genai.Client(credentials=creds)

        print("Testing minimal generate_content...")
        # Use gemini-2.0-flash-lite if available, or 1.5-flash
        response = client.models.generate_content(
            model="gemini-1.5-flash", contents='Say "OpenData v2 working"'
        )

        print("\n--- RESPONSE ---")
        print(response.text)
        print("----------------")

    except Exception as e:
        print(f"\nFAILED: {e}")


if __name__ == "__main__":
    test_v2()
