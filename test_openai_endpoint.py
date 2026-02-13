import sys
from pathlib import Path

# Add src to python path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

import requests
from opendata.workspace import WorkspaceManager


def test_endpoint():
    print("Loading settings via WorkspaceManager...")
    wm = WorkspaceManager()
    settings = wm.get_settings()

    # Extract OpenAI settings
    base_url = settings.openai_base_url
    model = settings.openai_model
    api_key = settings.openai_api_key or "dummy-key"

    if not base_url:
        print("Error: openai_base_url not found in settings.")
        return

    print(f"Testing Endpoint: {base_url}")
    print(f"Model: {model}")

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello, are you working?"}],
        "temperature": 0.7,
    }

    print("\nSending request (timeout=120s)...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            print(f"\nResponse:\n{content}")
        else:
            print(f"Error Response: {response.text}")

    except Exception as e:
        print(f"\nConnection Error: {e}")


if __name__ == "__main__":
    test_endpoint()
