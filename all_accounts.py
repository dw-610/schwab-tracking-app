"""This script shows a summary of all accounts for a profile."""

import argparse
import schwab_client


def print_all_accounts(profile: str = "default", verbose: bool = False):
    """Prints a summary of all accounts for the given profile.

    Args:
        profile: Profile name for multi-account support (default: "default")
        verbose: Whether to print debug messages (default: False)
    """

    client = schwab_client.SchwabClient(profile=profile, verbose=verbose)

    # Get all account numbers
    accounts = client.get_account_numbers()

    # Collect account data and calculate total
    account_data = []
    total_sum = 0.0

    for account_info in accounts:
        account_hash = account_info['hashValue']
        account_number = account_info['accountNumber']

        # Get account values
        values = client.get_account_values(account_hash)
        total = values['total']
        total_sum += total

        account_data.append({
            'number': account_number,
            'value': total
        })

    # Print header
    print("┌" + "─"*54 + "┐")
    print("│ Account                   Value           Percent    │")
    print("├" + "─"*54 + "┤")

    # Print each account with percentage
    for account in account_data:
        pct = (account['value'] / total_sum * 100) if total_sum > 0 else 0
        print(f"│ {account['number']:<24}  ${account['value']:>12,.2f}  ({pct:>5.1f}%)    │")

    # Print total
    print("├" + "─"*54 + "┤")
    print(f"│ {'TOTAL':<24}  ${total_sum:>12,.2f}  (100.0%)    │")
    print("└" + "─"*54 + "┘")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Show all accounts summary")
    parser.add_argument('profile',
                        help='Profile name for multi-account support')
    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Print debug messages')
    args = parser.parse_args()

    print_all_accounts(profile=args.profile, verbose=args.verbose)
