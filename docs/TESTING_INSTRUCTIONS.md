# Instruction for Testers: OpenData Tool (v0.9.3-beta)

This is a concept demo of the OpenData Agent. The goal is to test the **frictionless authentication**, **scientific file extraction**, the **iterative chat loop**, and the **metadata packaging**.

## 1. Setup (First time only)
... [Standard setup instructions] ...

## 2. Launching the App
... [Standard launch instructions] ...

## 3. The \"Happy Path\" Test
1.  **Authorization:** Click **\"Sign in with Google\"** in the browser. Complete the OAuth flow.
2.  **Analysis:**
    -   Enter the demo path: `tests/fixtures/demo_project`
    -   Click **\"Analyze Directory\"**.
3.  **Interaction:** 
    -   The agent should greet you and identify the VASP/LaTeX files.
    -   Verify that **all authors** from the LaTeX file are listed on the right.
4.  **Packaging (New):**
    -   Click the green **\"Build Package\"** button on the right panel.
    -   If the metadata is incomplete, follow the AI's suggestions to fill it.
    -   Once valid, the browser should trigger a download of `rodbuk_package.zip`.
    -   **Verify:** Open the ZIP. It should contain `metadata.yaml`, `metadata.json`, and any `README/LICENSE` files, but **no .csv or .dat research data**.

## 4. Reporting Issues
Please note any layout \"jumping,\" AI errors, or extraction failures. This is a concept demo; bugs are expected!
