"""This script performs authorization and outputs tokens for using the app."""

import argparse
import token_manager


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform OAuth authorization for Schwab API")
    parser.add_argument('--profile', default='default',
                        help='Profile name for multi-account support (default: "default")')
    args = parser.parse_args()

    # Perform OAuth flow to get initial tokens
    token_manager.perform_oauth_flow(profile=args.profile)
