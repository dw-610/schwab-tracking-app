"""Token management for Schwab API authentication.

This module handles OAuth token lifecycle including:
- Initial OAuth/PKCE authorization flow
- Token storage in secure directory
- Automatic token refresh when expired
"""

# Standard library
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

# Third-party
from dotenv import load_dotenv
from flask import Flask, request
import requests


# ====== Configuration ======
SECURE_DIR = Path.home() / ".config" / "schwab-oauth"
SECURE_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(SECURE_DIR / ".env")

# Schwab API credentials
APP_KEY = os.environ.get("SCHWAB_APP_KEY")
APP_SECRET = os.environ.get("SCHWAB_APP_SECRET")

# OAuth endpoints and settings
REDIRECT_URI = "https://127.0.0.1:8443/callback"
SCOPE = "readonly"
AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"

# SSL certificates (in secure directory)
CERT_FILE = str(SECURE_DIR / "127.0.0.1.pem")
KEY_FILE = str(SECURE_DIR / "127.0.0.1-key.pem")

# Token storage
def _get_tokens_file(profile: str = "default") -> Path:
    """Get the path to the tokens file for a given profile.

    Args:
        profile: Profile name for multi-account support (default: "default")

    Returns:
        Path: Path to the tokens file for this profile
    """
    return SECURE_DIR / f"tokens_{profile}.json"

# Use Basic Auth for token requests (recommended)
USE_BASIC_AUTH = True


# ====== Helper Functions ======
def _b64url(b: bytes) -> str:
    """Base64-URL encode bytes without padding."""
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _validate_credentials():
    """Validate that required credentials are present."""
    if not APP_KEY or not APP_SECRET:
        raise ValueError(
            "Missing credentials! Ensure SCHWAB_APP_KEY and SCHWAB_APP_SECRET "
            f"are set in {SECURE_DIR / '.env'}"
        )


# ====== Token Management ======
def get_valid_token(profile: str = "default") -> str:
    """Get a valid access token, automatically refreshing if expired.

    Args:
        profile: Profile name for multi-account support (default: "default")

    Returns:
        str: Valid access token for API requests

    Raises:
        FileNotFoundError: If tokens file doesn't exist (need to run OAuth flow first)
        ValueError: If credentials are missing
        Exception: If token refresh fails
    """
    _validate_credentials()

    tokens_file = _get_tokens_file(profile)
    with open(tokens_file) as f:
        tokens = json.load(f)

    # Check if token is expired
    saved_at = tokens.get("_saved_at", 0)
    expires_in = tokens.get("expires_in", 1800)  # Default 30min
    age = int(time.time()) - saved_at

    # If token still valid (with 60 second buffer), return it
    if age < (expires_in - 60):
        print(f'[token] Access token still valid ({expires_in - age}s remaining)')
        return tokens["access_token"]

    # Token expired, refresh it
    print("[token] Access token expired, refreshing...")

    # Make refresh token request
    data = {
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"]
    }

    # Use Basic Auth
    basic = base64.b64encode(f"{APP_KEY}:{APP_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    resp = requests.post(TOKEN_URL, data=data, headers=headers, timeout=20)

    if not resp.ok:
        raise Exception(f"Token refresh failed: {resp.status_code} - {resp.text}")

    # Save new tokens
    new_tokens = resp.json()
    new_tokens["_saved_at"] = int(time.time())
    with open(tokens_file, "w") as f:
        json.dump(new_tokens, f, indent=2)
    os.chmod(tokens_file, 0o600)

    print("[token] Access token refreshed successfully")
    return new_tokens["access_token"]


# ====== OAuth Flow ======
def perform_oauth_flow(profile: str = "default"):
    """Perform the initial OAuth authorization flow with PKCE.

    This starts a local HTTPS server, opens a browser for user authorization,
    and exchanges the authorization code for access and refresh tokens.

    The tokens are saved to the secure directory for future use.

    Args:
        profile: Profile name for multi-account support (default: "default")
    """
    _validate_credentials()

    tokens_file = _get_tokens_file(profile)

    # Generate PKCE challenge
    code_verifier = secrets.token_urlsafe(64)  # 43-128 chars
    code_challenge = _b64url(hashlib.sha256(code_verifier.encode()).digest())
    state = secrets.token_urlsafe(16)

    # Build authorize URL
    params = {
        "response_type": "code",
        "client_id": APP_KEY,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"{AUTH_URL}?" + urllib.parse.urlencode(
        params, quote_via=urllib.parse.quote)

    # Create Flask app for callback
    app = Flask(__name__)

    @app.route("/callback")
    def callback():
        code = request.args.get("code")
        ret_state = request.args.get("state")

        if not code:
            return "Missing code", 400
        if ret_state != state:
            return "State mismatch", 400

        print("\n[callback] Got code:", code, flush=True)

        # Exchange authorization code for tokens
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        }

        if USE_BASIC_AUTH:
            basic = base64.b64encode(f"{APP_KEY}:{APP_SECRET}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"
        else:
            data["client_id"] = APP_KEY
            if APP_SECRET:
                data["client_secret"] = APP_SECRET

        resp = requests.post(TOKEN_URL, data=data, headers=headers, timeout=20)
        print("[token] status:", resp.status_code, flush=True)
        print("[token] body:", resp.text, flush=True)

        if resp.ok:
            try:
                payload = resp.json()
                payload["_saved_at"] = int(time.time())
                with open(tokens_file, "w") as f:
                    json.dump(payload, f, indent=2)
                os.chmod(tokens_file, 0o600)
                print(f"[token] Saved tokens to {tokens_file}", flush=True)
            except Exception as e:
                print("[token] couldn't parse/save JSON:", e, flush=True)
            return "Tokens received  you can close this tab. Check your console.", 200
        else:
            return f"Token exchange failed ({resp.status_code}). See console.", 400

    def run_server():
        app.run(host="127.0.0.1", port=8443, ssl_context=(CERT_FILE, KEY_FILE))

    # Start server and open browser
    print("Authorize URL (auto-opening):\n", authorize_url, flush=True)
    threading.Thread(target=run_server, daemon=True).start()
    webbrowser.open_new(authorize_url)
    print("\nWaiting for callback...", flush=True)

    # Keep the process alive
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    # When run directly, perform OAuth flow
    perform_oauth_flow()
