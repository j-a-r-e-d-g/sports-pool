# sheets_reader.py
# Reads pool picks from the Google Sheet linked to the form.
# This lets us edit responses directly in the sheet (e.g. fix a tiebreaker).
#
# Sheet columns (from the Google Form):
#   A: Timestamp
#   B: Your Name
#   C-D: Tier 1 picks (1 of 2, 2 of 2)
#   E-F: Tier 2 picks
#   G-H: Tier 3 picks
#   I-J: Tier 4 picks
#   K-L: Tier 5 picks
#   M: Tiebreaker prediction

import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Same scopes as form_generator — reuses the same token
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "credentials.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "form_config.json")


def _is_cloud():
    """Detect if we're running on Streamlit Cloud."""
    return os.path.exists("/mount/src")


def authenticate():
    """
    Load saved credentials. Supports two modes:
    - Streamlit Cloud: reads token from st.secrets["google_token"]
    - Local: reads token.json from disk
    """
    creds = None
    on_cloud = _is_cloud()

    # Try Streamlit secrets first (for cloud deployment)
    try:
        import streamlit as st
        if "google_token" in st.secrets:
            token_data = dict(st.secrets["google_token"])
            token_data["scopes"] = SCOPES
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)

            # Refresh if expired
            if creds and not creds.valid and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            return creds
    except Exception as e:
        if on_cloud:
            raise RuntimeError(f"Cloud auth failed: {e}")

    # Local only from here — never touch filesystem on cloud
    if on_cloud:
        raise RuntimeError("No google_token found in Streamlit secrets")

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    if creds is None or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


# Spreadsheet ID for the Google Sheet linked to the form
SPREADSHEET_ID = "1Zh-Thre-zsy6w7dIcm4h_xlEep58cl7LYWKiANRkWyA"


def get_spreadsheet_id():
    """
    Get the spreadsheet ID. Checks Streamlit secrets first (for cloud),
    falls back to the hardcoded default.
    """
    try:
        import streamlit as st
        if "form_config" in st.secrets:
            return st.secrets["form_config"].get("spreadsheet_id", SPREADSHEET_ID)
    except Exception:
        pass
    return SPREADSHEET_ID


def fetch_picks(creds=None):
    """
    Read picks from the Google Sheet linked to the form.
    Edits made directly in the sheet are picked up immediately.

    Returns a list of dicts:
        [
            {
                "name": "Jared",
                "picks": ["Player 1", "Player 2", ... 10 total],
                "tiebreaker": -12,
            },
            ...
        ]
    """
    if creds is None:
        creds = authenticate()

    spreadsheet_id = get_spreadsheet_id()

    # Build the Sheets API service
    sheets_service = build("sheets", "v4", credentials=creds)

    # Read all rows (skip header row)
    # Columns: A=Timestamp, B=Name, C-L=Picks (10), M=Tiebreaker
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="A2:M",  # Start at row 2 to skip headers
    ).execute()

    rows = result.get("values", [])

    if not rows:
        print("No form responses yet.")
        return []

    participants = []
    for row in rows:
        # Pad row in case some cells are empty at the end
        while len(row) < 13:
            row.append("")

        name = row[1].strip()  # Column B
        picks = [cell.strip() for cell in row[2:12]]  # Columns C-L (10 picks)
        tb_value = row[12].strip()  # Column M

        # Parse tiebreaker as int
        try:
            tiebreaker = int(tb_value)
        except (ValueError, TypeError):
            tiebreaker = 0

        if name:  # Skip empty rows
            participants.append({
                "name": name,
                "picks": picks,
                "tiebreaker": tiebreaker,
            })

    print(f"Loaded {len(participants)} picks from Google Sheet.")
    return participants


# Quick test: run this file directly to see the parsed responses
if __name__ == "__main__":
    participants = fetch_picks()
    for p in participants:
        print(f"\n{p['name']} (tiebreaker: {p['tiebreaker']}):")
        for i, pick in enumerate(p["picks"]):
            tier = (i // 2) + 1
            print(f"  Tier {tier}: {pick}")
