"""Schwab API Client for account and trading data.

This module provides a clean interface for interacting with the Schwab API.
Authentication is handled automatically via token_manager.
"""

import requests
from typing import Optional

import token_manager


class SchwabClient:
    """Client for interacting with Schwab Trader API.

    Handles authentication automatically using token_manager.
    """

    BASE_URL = "https://api.schwabapi.com/trader/v1"

    def __init__(self, profile: str = "default"):
        """Initialize the Schwab API client.

        Args:
            profile: Profile name for multi-account support (default: "default")
        """
        self.profile = profile

    def _get_headers(self) -> dict:
        """Get headers with valid authentication token.

        Returns:
            dict: Headers including Authorization bearer token
        """
        access_token = token_manager.get_valid_token(profile=self.profile)
        return {"Authorization": f"Bearer {access_token}"}

    def get_account_numbers(self) -> list:
        """Get all account numbers for the authenticated user.

        Returns:
            list: List of account information dictionaries

        Raises:
            requests.HTTPError: If the API request fails
        """
        resp = requests.get(
            f"{self.BASE_URL}/accounts/accountNumbers",
            headers=self._get_headers()
        )
        print(f'[SchwabClient] get_account_numbers status: {resp.status_code}')
        resp.raise_for_status()
        return resp.json()

    def get_account_data(
        self,
        account_number: str,
        include_positions: bool = True
    ) -> dict:
        """Get account data including balances and optionally positions.

        Args:
            account_number: The account number to retrieve data for
            include_positions: Whether to include position details (default: True)

        Returns:
            dict: Account data including balances and positions

        Raises:
            requests.HTTPError: If the API request fails
        """
        params = {}
        if include_positions:
            params["fields"] = "positions"

        resp = requests.get(
            f"{self.BASE_URL}/accounts/{account_number}",
            headers=self._get_headers(),
            params=params
        )
        print(f'[SchwabClient] get_account_data status: {resp.status_code}')
        resp.raise_for_status()
        return resp.json()

    def get_account_values(self, account_number: str) -> dict:
        """Get simplified account values including total, cash, and positions.

        This is a convenience method that extracts the most commonly needed
        values from the full account data.

        Args:
            account_number: The account number to retrieve values for

        Returns:
            dict: Dictionary with keys:
                - total (float): Total liquidation value
                - cash (float): Total cash balance
                - positions (dict): Symbol -> market value mapping

        Raises:
            requests.HTTPError: If the API request fails
        """
        data = self.get_account_data(account_number, include_positions=True)

        values = {}

        # Get total account value
        aggregated = data["aggregatedBalance"]
        values['total'] = aggregated['liquidationValue']

        # Get cash and positions
        securities = data["securitiesAccount"]
        values['cash'] = securities['currentBalances']['totalCash']

        # Extract position values
        positions = securities.get('positions', [])
        positions_dict = {}
        for pos in positions:
            positions_dict[pos['instrument']['symbol']] = pos['marketValue']
        values['positions'] = positions_dict

        return values


# Convenience function for backward compatibility
def get_client() -> SchwabClient:
    """Get a new SchwabClient instance.

    Returns:
        SchwabClient: New client instance
    """
    return SchwabClient()
