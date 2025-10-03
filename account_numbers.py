"""Script to retrieve and display account numbers."""

import json
import schwab_client


def print_info():
    """Prints all account information as JSON."""

    client = schwab_client.SchwabClient()
    data = client.get_account_numbers()
    print(json.dumps(data, indent=4, sort_keys=False))


if __name__=="__main__":
    print_info()
