# Python Schwab Tracking App

The purpose of this app is to track Schwab accounts using the developer portal.

## Usage

### status.py

Display account status with portfolio values and targets:

```bash
python status.py <profile> <account>
```

**Arguments:**
- `profile`: Profile name for multi-account support
- `account`: Account to display status for (choices: CUSTODIAL, INVESTING, ROTH, ROTH2, IRA)

**Example:**
```bash
python status.py default ROTH
```

# Environment Variables

oauth_end_to_end.py requires two environment variables, `SCHWAB_APP_KEY` AND `SCHWAB_APP_SECRET` with your corresponding application key and secret.