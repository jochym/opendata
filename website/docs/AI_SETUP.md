# Developer Setup: AI & OAuth2

To enable the AI features (Gemini) and the frictionless "Sign in with Google" flow, follow these steps to configure your environment.

## 1. Google Cloud vs. AI Studio
- **AI Studio:** Used for generating personal API Keys. (Avoid for this project).
- **Google Cloud Console:** Used for creating **OAuth2 Credentials** (Required for the frictionless "Sign in" experience).

## 2. Google Cloud Project Setup
1.  Go to the [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials).
2.  Find the project automatically created by AI Studio (e.g., `Generative Language Client`) or create a new one.
3.  Go to **OAuth consent screen**:
    -   Select **External**.
    -   Fill in the required app name (`OpenData Tool`) and support email.
    -   Add the scope: `https://www.googleapis.com/auth/generative-language`.
    -   Under **Test users**, add your own email address.

## 3. Create Credentials
1.  Go to **Credentials**.
2.  Click **Create Credentials > OAuth client ID**.
3.  Select **Desktop app**.
4.  Download the resulting JSON file and rename it to `client_secrets.json`.

## 4. Secret File Management
**CRITICAL:** Never commit secret files to Git.

1.  **Location:** Place the file in: `/home/jochym/.opendata_tool/client_secrets.json`.

## 4. Troubleshooting
- If you see "App not verified," click **Advanced > Go to OpenData Tool (unsafe)**. This is normal during development.
- The first successful login will create a `token.json` in the same directory. This token allows the tool to stay logged in without re-authenticating.
