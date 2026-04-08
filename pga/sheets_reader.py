# sheets_reader.py
# Reads pool picks from Google Form responses via the Forms API.
# Parses responses into the same format the scoring engine expects.
#
# The form has these questions in order:
#   1. Your Name
#   2-3. Tier 1 picks (1 of 2, 2 of 2)
#   4-5. Tier 2 picks
#   6-7. Tier 3 picks
#   8-9. Tier 4 picks
#   10-11. Tier 5 picks
#   12. Tiebreaker prediction

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


def authenticate():
    """
    Load saved credentials. Supports two modes:
    - Streamlit Cloud: reads token from st.secrets["google_token"]
    - Local: reads token.json from disk
    """
    creds = None

    # Try Streamlit secrets first (for cloud deployment)
    try:
        import streamlit as st
        if "google_token" in st.secrets:
            token_data = dict(st.secrets["google_token"])
            # Ensure scopes are present — Streamlit secrets may not have them
            token_data["scopes"] = SCOPES
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    except Exception as e:
        print(f"Secrets auth failed: {e}")

    # Fall back to local token file
    if creds is None and os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh expired credentials
    if creds and not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token locally if possible
        try:
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        except OSError:
            pass  # Can't write on Streamlit Cloud, that's fine

    # Only try interactive auth locally as a last resort
    if (creds is None or not creds.valid) and os.path.exists(CREDENTIALS_FILE):
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def load_form_config():
    """
    Load the form ID. Checks in order:
    1. Streamlit secrets (for cloud)
    2. form_config.json file (for local)
    """
    # Try Streamlit secrets first
    try:
        import streamlit as st
        if "form_config" in st.secrets:
            return dict(st.secrets["form_config"])
    except Exception:
        pass

    # Fall back to local file
    if not os.path.exists(CONFIG_FILE):
        print("No form_config.json found. Run form_generator.py first.")
        return None

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def get_question_order(forms_service, form_id):
    """
    Get the form's question IDs in order so we can map responses
    to the right fields (name, tier picks, tiebreaker).
    """
    form = forms_service.forms().get(formId=form_id).execute()
    question_ids = []

    for item in form.get("items", []):
        question = item.get("questionItem", {}).get("question", {})
        question_id = question.get("questionId")
        if question_id:
            question_ids.append(question_id)

    return question_ids


def fetch_picks(creds=None):
    """
    Fetch all form responses and parse them into the participant format
    expected by the scoring engine.

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

    config = load_form_config()
    if not config:
        return []

    form_id = config["form_id"]

    # Build the Forms API service
    forms_service = build("forms", "v1", credentials=creds)

    # Get question IDs in order so we can map responses correctly
    question_ids = get_question_order(forms_service, form_id)

    # question_ids should be in this order:
    # [0] = Name
    # [1-2] = Tier 1 picks
    # [3-4] = Tier 2 picks
    # [5-6] = Tier 3 picks
    # [7-8] = Tier 4 picks
    # [9-10] = Tier 5 picks
    # [11] = Tiebreaker

    if len(question_ids) < 12:
        print(f"Expected 12 questions, found {len(question_ids)}. Form may be misconfigured.")
        return []

    name_qid = question_ids[0]
    pick_qids = question_ids[1:11]  # 10 pick questions
    tiebreaker_qid = question_ids[11]

    # Fetch all responses
    responses = forms_service.forms().responses().list(formId=form_id).execute()
    response_list = responses.get("responses", [])

    if not response_list:
        print("No form responses yet.")
        return []

    participants = []
    for response in response_list:
        answers = response.get("answers", {})

        # Extract the participant's name
        name_answer = answers.get(name_qid, {})
        name = name_answer.get("textAnswers", {}).get("answers", [{}])[0].get("value", "Unknown")

        # Extract all 10 picks
        picks = []
        for qid in pick_qids:
            pick_answer = answers.get(qid, {})
            pick_value = pick_answer.get("textAnswers", {}).get("answers", [{}])[0].get("value", "")
            picks.append(pick_value)

        # Extract tiebreaker prediction
        tb_answer = answers.get(tiebreaker_qid, {})
        tb_value = tb_answer.get("textAnswers", {}).get("answers", [{}])[0].get("value", "0")

        # Parse tiebreaker as int (handle both "-12" and "12" formats)
        try:
            tiebreaker = int(tb_value)
        except ValueError:
            tiebreaker = 0

        participants.append({
            "name": name,
            "picks": picks,
            "tiebreaker": tiebreaker,
        })

    print(f"Loaded {len(participants)} picks from Google Form responses.")
    return participants


# Quick test: run this file directly to see the parsed responses
if __name__ == "__main__":
    participants = fetch_picks()
    for p in participants:
        print(f"\n{p['name']} (tiebreaker: {p['tiebreaker']}):")
        for i, pick in enumerate(p["picks"]):
            tier = (i // 2) + 1
            print(f"  Tier {tier}: {pick}")
