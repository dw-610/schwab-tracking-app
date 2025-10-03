"""This script shows the basic status of an account."""

import os
import json
import argparse
from pathlib import Path

from dotenv import load_dotenv
from config import TARGETS
import schwab_client


# Load environment variables
SECURE_DIR = Path.home() / ".config" / "schwab-oauth"
load_dotenv(SECURE_DIR / ".env")

# Account numbers from environment
CUSTODIAL = os.environ.get("ACCT_NUM_CUST")
INVESTING = os.environ.get("ACCT_NUM_INVST")
ROTH = os.environ.get("ACCT_NUM_ROTH")
ROTH2 = os.environ.get("ACCT_NUM_ROTH2")
IRA = os.environ.get("ACCT_NUM_IRA")


def print_line(name: str, value: float, total: float, target_percent: float = None):
    """Helper function to print lines in the status table."""

    percent = value/total*100

    if target_percent is not None:
        target_value = target_percent*total
        target_percent_display = target_percent * 100
        delta = target_value - value
        print(
            f'│ {name:<6}'
            f'{value:>10.2f}'
            f'{percent:>7.2f}%'
            f'{target_percent_display:4.0f}%'
            f'{target_value:>10.2f}'
            f'{delta:>10.2f} │'
        )
    else:
        print(
            f'│ {name:<6}'
            f'{value:>10.2f}'
            f'{percent:>7.2f}% │'
        )


def print_status(values: dict, targets: dict = None):
    """Formats and prints the status table given the output of get_account_values."""

    # print table header
    if targets is not None:
        print("┌" + "─"*51 + "┐")
        print("│ Asset      Value     %   Tgt%    Target     Delta │")
        print("├" + "─"*51 + "┤")
    else:
        print("┌" + "─"*26 + "┐")
        print("│ Asset      Value     %   │")
        print("├" + "─"*26 + "┤")

    total = values['total']  # Total account value

    cash = values['cash']  # Cash value
    print_line('Cash', cash, total, 0.0 if targets is not None else None)

    # print information on the positions in the account
    for symbol, val in values['positions'].items():
        target_pct = targets.get(symbol) if targets is not None else None
        print_line(symbol, val, total, target_pct)

    if targets is not None:
        print("├" + "─"*51 + "┤")
        print_line('TOTAL', total, total, 1.0)
        print("└" + "─"*51 + "┘")
    else:
        print("├" + "─"*26 + "┤")
        print_line('TOTAL', total, total)
        print("└" + "─"*26 + "┘")


def print_all(account_number: str):
    """Prints all of the JSON for an account."""

    client = schwab_client.SchwabClient()
    data = client.get_account_data(account_number, include_positions=True)
    print(json.dumps(data, indent=4, sort_keys=False))


if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Show account status")
    parser.add_argument('account', choices=['CUSTODIAL', 'INVESTING', 'ROTH', 'ROTH2', 'IRA'],
                        help='Account to display status for')
    args = parser.parse_args()

    accounts = {
        'CUSTODIAL': CUSTODIAL,
        'INVESTING': INVESTING,
        'ROTH': ROTH,
        'ROTH2': ROTH2,
        'IRA': IRA
    }

    client = schwab_client.SchwabClient()
    values = client.get_account_values(accounts[args.account])

    # Check if targets exist for this account
    targets = TARGETS.get(args.account)

    print_status(values, targets)
