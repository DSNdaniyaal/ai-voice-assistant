from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SRC_DIR = Path(__file__).resolve().parents[1]

CREDENTIALS_PATH = SRC_DIR / "credentials.json"
TOKEN_PATH = SRC_DIR / "token.json"
ENV_PATH = SRC_DIR / ".env"

load_dotenv(ENV_PATH)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
]

def get_google_credentials():

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_PATH),
            SCOPES,
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:

            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at:\n"
                    f"{CREDENTIALS_PATH}"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH),
                SCOPES,
            )

            creds = flow.run_local_server(
                port=0
            )
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return creds