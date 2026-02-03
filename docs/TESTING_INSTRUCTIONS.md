# Instruction for Testers: OpenData Tool (v0.2.0)

This is an early concept demo of the OpenData Agent. The goal is to test the **frictionless authentication**, **scientific file extraction**, and the **iterative chat loop**.

## 1. Setup (First time only)
Ensure you have the following in place:
- **Python 3.10+** installed.
- **Dependencies:** Run `pip install -e .` in your virtual environment.
- **Secrets:** Place your `client_secrets.json` from the Google Cloud Console into `~/.opendata_tool/`.

## 2. Launching the App
Run the tool from your terminal:
```bash
source venv/bin/activate
python3 src/opendata/main.py
```
*Note: If you are working remotely without an X session, use the `--no-gui` flag.*

## 3. The "Happy Path" Test
1.  **Authorization:** Click **"Sign in with Google"** in the browser. Complete the OAuth flow.
2.  **Analysis:**
    -   Enter the demo path: `/home/jochym/Projects/OpenData/tests/fixtures/demo_project`
    -   Click **"Analyze Directory"**.
3.  **Interaction:** 
    -   The agent should greet you and identify the VASP/LaTeX files.
    -   Verify that **all authors** from the LaTeX file are listed on the right.
    -   Verify that ORCIDs are hidden behind the green checkmark tooltips.
4.  **External Tools:** 
    -   Type: *"Search for the ORCID of John Doe"* to test ORCID search.
    -   Type: *"The paper is on arXiv 2101.00001"* to test automated metadata fetching.
5.  **Robustness:** Switch models in the top header during the chat. The agent should maintain the context.

## 4. Reporting Issues
Please note any layout "jumping," AI errors, or extraction failures. This is a concept demo; bugs are expected!
