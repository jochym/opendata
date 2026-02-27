# Task: Include OAuth2 Secrets in PyPI Package

## Goal
Enable the PyPI package (`opendata-tool`) to include `client_secrets.json` during GitHub Actions build, eliminating the need for manual distribution of this file to users.

## Context
- The app uses OAuth2 for Google AI authentication
- Current code already supports multiple secret sources (env vars, bundled file, user-provided file)
- `pyproject.toml` already configured to include `*.json` files from `src/opendata/` in the package
- Binary builds (PyInstaller/pyApp) already inject secrets during CI/CD build
- PyPI build job needs the same treatment

## Required Changes

### 1. Modify `.github/workflows/main.yml`

Add a step to inject `client_secrets.json` in the `build-pypi` job before running `python -m build`.

**Location:** Line ~242 (inside `build-pypi` job, after "Set up Python" step)

**Add this step:**
```yaml
- name: Prepare client_secrets.json
  shell: bash
  env:
    GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
    GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
  run: |
    if [ -n "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ]; then
      echo "{\"installed\":{\"client_id\":\"$GOOGLE_CLIENT_ID\",\"project_id\":\"opendata-tool\",\"auth_uri\":\"https://accounts.google.com/o/oauth2/auth\",\"token_uri\":\"https://oauth2.googleapis.com/token\",\"auth_provider_x509_cert_url\":\"https://www.googleapis.com/oauth2/v1/certs\",\"client_secret\":\"$GOOGLE_CLIENT_SECRET\",\"redirect_uris\":[\"http://localhost\"]}}" > src/opendata/client_secrets.json
      echo "[INFO] client_secrets.json created for PyPI build"
    else
      echo "{}" > src/opendata/client_secrets.json
      echo "[WARN] GOOGLE_CLIENT_ID/SECRET not found, creating empty secrets file"
    fi
```

### 2. Verify `pyproject.toml` Configuration

**Location:** Line 75-76

**Ensure this exists:**
```toml
[tool.setuptools.package-data]
"opendata" = ["prompts/*.md", "ui/**/*", "VERSION", "*.json"]
```

This should already be present - verify it includes `*.json`.

### 3. Add GitHub Repository Secrets (Manual Step)

**Repository Admin must add these secrets:**
1. Go to: `https://github.com/jochym/opendata/settings/secrets/actions`
2. Add `GOOGLE_CLIENT_ID` (from Google Cloud Console OAuth2 credentials)
3. Add `GOOGLE_CLIENT_SECRET` (from Google Cloud Console OAuth2 credentials)

**Format of secrets:**
- `GOOGLE_CLIENT_ID`: Looks like `123456789-abc123def456.apps.googleusercontent.com`
- `GOOGLE_CLIENT_SECRET`: Looks like `GOCSPX-abc123def456`

## Testing

### Before Mging:
1. **Verify syntax:** Run `yamllint .github/workflows/main.yml` (if available) or check YAML syntax
2. **Check existing tests:** `pytest` should still pass
3. **Verify package-data:** Run `python -m build` locally and inspect the `.whl` file:
   ```bash
   python -m build
   unzip -l dist/opendata_tool-*.whl | grep client_secrets
   ```
   (Create a temporary `src/opendata/client_secrets.json` locally to test)

### After Merging (on next tag release):
1. Create a test tag: `git tag v0.X.Y-test && git push origin v0.X.Y-test`
2. Check GitHub Actions log for `build-pypi` job
3. Verify the step "Prepare client_secrets.json" runs successfully
4. Download the built artifact and verify it contains `client_secrets.json`

## Security Notes

- **OAuth2 "Installed Application" type:** Google allows embedded secrets for desktop apps
- **Secrets are public in PyPI package:** Anyone can extract them from the wheel file
- **Mitigation:**
  - Restrict OAuth2 credentials to only necessary scopes
  - Monitor usage in Google Cloud Console
  - Consider rotating secrets periodically
- **Secrets NEVER committed to git:** File is in `.gitignore`, only exists in CI/CD runtime

## Files to Modify
- `.github/workflows/main.yml` (add secrets injection step to `build-pypi` job)

## Files to Verify (no changes needed)
- `pyproject.toml` (already configured correctly)
- `src/opendata/ai/google_provider.py` (already uses bundled secrets)
- `src/opendata/ai/genai_provider.py` (already uses bundled secrets)
- `.gitignore` (already excludes `client_secrets.json`)

## Acceptance Criteria
- [ ] `build-pypi` job creates `src/opendata/client_secrets.json` during build
- [ ] Built `.whl` file contains `client_secrets.json` in the root of the package
- [ ] Built `.tar.gz` (sdist) contains `client_secrets.json` in `src/opendata/`
- [ ] PyPI package works with OAuth2 flow without requiring manual file placement
- [ ] Fallback behavior works if secrets are not configured (graceful degradation)

## Reference Implementation
See existing secrets injection in:
- `.github/workflows/pyapp-build-binary.yml` (lines 66-75)
- `.github/workflows/reusable-build-binary.yml` (lines 38-49)
- `scripts/generate_spec.py` (local build script with same logic)
