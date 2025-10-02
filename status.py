"""This script shows the basic status of an account."""

import os
import time
import json
import base64
import requests
from pathlib import Path

from dotenv import load_dotenv
from config import TARGETS

load_dotenv()


TOKEN_DIR = Path.home() / ".config" / "schwab-oauth"
TOKENS_FILE = TOKEN_DIR / "tokens.json"

CUSTODIAL = os.environ.get("ACCT_NUM_CUST")
INVESTING = os.environ.get("ACCT_NUM_INVST")
ROTH = os.environ.get("ACCT_NUM_ROTH")
ROTH2 = os.environ.get("ACCT_NUM_ROTH2")


def get_valid_token() -> str:
    """Gets a valid access token, refreshing if necessary."""

    with open(TOKENS_FILE) as f:
        tokens = json.load(f)

    # Check if token is expired
    saved_at = tokens.get("_saved_at", 0)
    expires_in = tokens.get("expires_in", 1800) # Default 30min
    age = int(time.time()) - saved_at

    # If token still valid (with 60 second buffer), return it
    if age < (expires_in - 60):
        print(f'[token] Access token still valid ({expires_in - age}s remaining)')
        return tokens["access_token"]
    
    # Token expired, refresh it
    print("[token] Access token expired, refreshing...")

    APP_KEY = os.environ.get("SCHWAB_APP_KEY")
    APP_SECRET = os.environ.get("SCHWAB_APP_SECRET")

    if not APP_KEY or not APP_SECRET:
        raise ValueError("Missing SCHWAB_APP_KEY or SCHWAB_APP_SECRET")

    # Make refresh token request
    data = {
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"]
    }

    # Use Basic Auth (same as oauth.py)
    basic = base64.b64encode(f"{APP_KEY}:{APP_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    resp = requests.post(
        "https://api.schwabapi.com/v1/oauth/token",
        data=data,
        headers=headers,
        timeout=20
    )

    if not resp.ok:
        raise Exception(f"Token refresh failed: {resp.status_code} - {resp.text}")
    
    # Save new tokens
    new_tokens = resp.json()
    new_tokens["_saved_at"] = int(time.time())
    with open(TOKENS_FILE, "w") as f:
        json.dump(new_tokens, f, indent=2)
    os.chmod(TOKENS_FILE, 0o600)

    print("[token] Access token refreshed successfully")
    return new_tokens["access_token"]


def get_values(account_number: str) -> dict:
    """Gets the positions and the amounts for the provided account."""

    access_token = get_valid_token()

    resp = requests.get(
        f"https://api.schwabapi.com/trader/v1/accounts/{account_number}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "positions"}
    )
    print(f'[get_values] GET status code: {resp.status_code}')
    
    data = resp.json()

    values = {}

    aggregated = data["aggregatedBalance"]
    values['total'] = aggregated['liquidationValue']

    securities = data["securitiesAccount"]
    values['cash'] = securities['currentBalances']['totalCash']
    positions = securities['positions']
    positions_dict = {}
    for pos in positions:
        positions_dict[pos['instrument']['symbol']] = pos['marketValue']
    values['positions'] = positions_dict
    
    return values


def print_line(name: str, value: float, total: float, target_percent: float):
    """Helper function to print lines in the status table."""

    percent = value/total*100
    target_value = target_percent*total
    target_percent *= 100
    delta = target_value - value
    print(
        f'│ {name:<6}'
        f'{value:>10.2f}'
        f'{percent:>7.2f}%'
        f'{target_percent:4.0f}%'
        f'{target_value:>10.2f}'
        f'{delta:>10.2f} │'
    )


def print_status(values: dict, targets: dict):
    """Formats and prints the status table given the output of get_values."""

    # print table header
    print("┌" + "─"*51 + "┐")
    print("│ Asset      Value     %   Tgt%    Target     Delta │")
    print("├" + "─"*51 + "┤")

    total = values['total']  # Total account value

    cash = values['cash']  # Cash value
    print_line('Cash', cash, total, 0.0)

    # print information on the positions in the account
    for symbol, val in values['positions'].items():
        print_line(symbol, val, total, targets[symbol])\
        
    print("├" + "─"*51 + "┤")
    print_line('TOTAL', total, total, 1.0)
    print("└" + "─"*51 + "┘")


def print_all(account_number: str):
    """Prints all of the JSON for an account."""

    access_token = get_valid_token()

    resp = requests.get(
        f"https://api.schwabapi.com/trader/v1/accounts/{account_number}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"fields": "positions"}
    )
    print(f'[get_values] GET status code: {resp.status_code}')
    
    data = resp.json()

    print(json.dumps(data, indent=4, sort_keys=False))


if __name__=="__main__":

    targets = {
        'SCHH': 0.10,
        'SCHP': 0.05,
        'VBK': 0.15,
        'VTC': 0.10,
        'VWO': 0.15,
        'SWISX': 0.20,
        'SWPPX': 0.20,
        'SWVXX': 0.05,
    }
    
    values = get_values(ROTH)
    print_status(values, TARGETS)
