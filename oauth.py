"""This script performs authorization and outputs tokens for using the app."""

import token_manager


if __name__ == "__main__":
    # Perform OAuth flow to get initial tokens
    token_manager.perform_oauth_flow()
