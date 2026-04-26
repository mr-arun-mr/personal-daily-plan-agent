"""
One-time Google Calendar OAuth2 setup script.

Run this once to authorize the bot to read your Google Calendar:
    python setup_calendar.py

Prerequisites:
1. Create a project at https://console.cloud.google.com
2. Enable the Google Calendar API
3. Create OAuth 2.0 credentials (Desktop App type)
4. Download the credentials JSON and save as credentials.json
"""
import os
import sys

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = "token.json"


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: {CREDENTIALS_FILE} not found.")
        print()
        print("To set up Google Calendar integration:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a new project (or select an existing one)")
        print("3. Enable the Google Calendar API:")
        print("   APIs & Services → Library → search 'Google Calendar API' → Enable")
        print("4. Create OAuth 2.0 credentials:")
        print("   APIs & Services → Credentials → Create Credentials → OAuth client ID")
        print("   Application type: Desktop App")
        print(f"5. Download the JSON file and save it as: {CREDENTIALS_FILE}")
        print("6. Run this script again: python setup_calendar.py")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        print("ERROR: Google auth libraries not installed.")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.valid:
        print("✅ Google Calendar already authorized and token is valid.")
        return

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing expired token…")
        creds.refresh(Request())
    else:
        print("Opening browser for Google Calendar authorization…")
        print("(If no browser opens, check the URL printed below)")
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"✅ Authorization successful! Token saved to {TOKEN_FILE}")
    print("Your bot can now read your Google Calendar events.")


if __name__ == "__main__":
    main()
