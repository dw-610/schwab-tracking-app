"""This script performs authorization and outputs tokens for using the app."""

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

load_dotenv()

# ====== CONFIG ======
APP_KEY = os.environ.get("SCHWAB_APP_KEY")  # Schwab "App Key" (client_id)
APP_SECRET = os.environ.get("SCHWAB_APP_SECRET")  # Schwab "Secret"
if not APP_KEY or not APP_SECRET:
    raise ValueError(
        "Missing credentials! Ensure SCHWAB_APP_KEY and SCHWAB_APP_SECRET "
        "are set in your .env file"
    )

REDIRECT_URI = "https://127.0.0.1:8443/callback"
SCOPE = "readonly"
AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
CERT_FILE = "127.0.0.1.pem"
KEY_FILE  = "127.0.0.1-key.pem"
USE_BASIC_AUTH = True  

TOKEN_DIR = Path.home() / ".config" / "schwab-oauth"
TOKEN_DIR.mkdir(parents=True, exist_ok=True)
TOKENS_OUTFILE = TOKEN_DIR / "tokens.json"


# ====== PKCE + state ======
def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

code_verifier = secrets.token_urlsafe(64)  # 43-128 chars
code_challenge = b64url(hashlib.sha256(code_verifier.encode()).digest())
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


# ====== Flask app ======
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

    # --- Exchange immediately ---
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }

    if USE_BASIC_AUTH and APP_SECRET:
        basic = base64.b64encode(f"{APP_KEY}:{APP_SECRET}".encode()).decode()
        headers["Authorization"] = f"Basic {basic}"
    else:
        # Send client creds in body instead of Basic auth
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
            with open(TOKENS_OUTFILE, "w") as f:
                json.dump(payload, f, indent=2)
            # After saving:
            os.chmod(TOKENS_OUTFILE, 0o600)  # Restrict access to tokens
            print(f"[token] Saved tokens to {TOKENS_OUTFILE}", flush=True)
        except Exception as e:
            print("[token] couldn't parse/save JSON:", e, flush=True)
        return "Tokens received — you can close this tab. Check your console.", 200
    else:
        return f"Token exchange failed ({resp.status_code}). See console.", 400

def run_server():
    app.run(host="127.0.0.1", port=8443, ssl_context=(CERT_FILE, KEY_FILE))

if __name__ == "__main__":
    print("Authorize URL (auto-opening):\n", authorize_url, flush=True)
    # Start HTTPS server, then open browser
    threading.Thread(target=run_server, daemon=True).start()
    webbrowser.open_new(authorize_url)
    print("\nWaiting for callback...", flush=True)
    # Keep the process alive
    while True:
        time.sleep(3600)
