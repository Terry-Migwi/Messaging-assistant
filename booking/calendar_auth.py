# git/RAG/langchain/booking/calendar_auth.py

import os
import sys
import subprocess
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# __file__ is:       git/RAG/langchain/booking/calendar_auth.py
# one dirname up:    git/RAG/langchain/booking/
# two dirnames up:   git/RAG/langchain/          ← credentials.json lives here
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


def _open_windows_browser(url: str) -> bool:
    """
    Attempt to open a URL in the Windows browser from WSL.
    Returns True if the command ran without error, False otherwise.
    """
    try:
        # cmd.exe treats & as a command separator — ^& escapes it
        safe_url = url.replace("&", "^&")
        subprocess.run(
            ["cmd.exe", "/c", "start", safe_url],
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except Exception:
        return False


def get_calendar_service():
    """
    Returns an authenticated Google Calendar API service object.

    First run:  opens Windows browser for approval, saves token.json
    Later runs: loads token.json silently, refreshes if expired

    Returns:
        googleapiclient.discovery.Resource: authenticated calendar service
    """
    creds = None

    # Load existing token if it exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        logger.info("Loaded existing token from token.json")

    # If no valid token, go through auth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token exists but expired — refresh silently
            logger.info("Token expired — refreshing automatically")
            creds.refresh(Request())
        else:
            # No token at all — run auth flow
            logger.info("No token found — starting auth flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )

            # Generate the auth URL
            auth_url, _ = flow.authorization_url(
                prompt="consent",
                login_hint="migwiwangari@gmail.com"
                )

            # Try to open Windows browser — tell user to do it manually if it fails
            browser_opened = _open_windows_browser(auth_url)
            if not browser_opened:
                print("\nCould not open browser automatically.")
                print("Please open this URL manually in your browser:")
                print(f"\n  {auth_url}\n")

            # Start local server to catch Google's redirect
            # open_browser=False because we already handled it above
            creds = flow.run_local_server(
                port=8085,
                open_browser=False
            )

        # Save the token for next time
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        logger.info("Token saved to token.json")

    return build("calendar", "v3", credentials=creds)