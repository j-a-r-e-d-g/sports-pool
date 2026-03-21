# form_generator.py
# Reads the locked masters_tiers.csv and creates a Google Form
# with dropdown questions for each tier (2 picks per tier) + tiebreaker.
#
# Usage:
#   1. Run tier_generator.py to lock the tiers
#   2. Run this script: python3 pga/form_generator.py
#   3. First run will open a browser for Google auth — sign in and authorize
#   4. The form URL will be printed when done
#
# Requires: credentials.json in the project root (OAuth desktop client)

import os
import csv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scopes needed: create forms, read responses from linked Google Sheet
SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

# Paths relative to the project root
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, "credentials.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "token.json")
TIERS_CSV = os.path.join(os.path.dirname(__file__), "masters_tiers.csv")


def authenticate():
    """
    Handle Google OAuth flow.
    First run opens a browser to sign in. After that, the token is saved
    to token.json so you don't have to sign in again.
    """
    creds = None

    # Check if we already have a saved token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid token, run the auth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the token for next time
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def load_tiers():
    """
    Read masters_tiers.csv and group players by tier.
    Returns a dict: { tier_number: [list of player names] }
    """
    tiers = {}
    with open(TIERS_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tier = int(row["tier"])
            name = row["name"]
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append(name)
    return tiers


def create_form(creds, tiers):
    """
    Create a Google Form with:
    - Name field
    - 2 dropdown questions per tier (Pick 1 and Pick 2)
    - Tiebreaker question (predicted winning score)
    """
    # Build the Forms API service
    forms_service = build("forms", "v1", credentials=creds)

    # Step 1: Create a blank form with a title
    form = forms_service.forms().create(body={
        "info": {
            "title": "2026 Masters Pool Picks",
        }
    }).execute()

    form_id = form["formId"]
    print(f"Form created: {form_id}")

    # Step 2: Build all the questions as batch update requests
    requests = []
    question_index = 0

    # Add a description at the top
    requests.append({
        "updateFormInfo": {
            "info": {
                "description": (
                    "Pick 2 players from each tier (10 total). "
                    "Scoring: cumulative to-par + missed cut penalty (+11) + "
                    "top 10 bonus (-10) + placement bonuses (1st: -15, 2nd: -14, "
                    "3rd: -13, 4th: -12, 5th: -11). "
                    "Tiebreaker: closest prediction to the winning score."
                ),
            },
            "updateMask": "description",
        }
    })

    # Name question
    requests.append({
        "createItem": {
            "item": {
                "title": "Your Name",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {
                            "paragraph": False,
                        }
                    }
                }
            },
            "location": {"index": question_index},
        }
    })
    question_index += 1

    # Tier labels for the form
    tier_labels = {
        1: "Tier 1 (Ranked 1–10)",
        2: "Tier 2 (Ranked 11–20)",
        3: "Tier 3 (Ranked 21–40)",
        4: "Tier 4 (Ranked 41–70)",
        5: "Tier 5 (Ranked 71+)",
    }

    # Add 2 dropdown questions per tier
    for tier_num in sorted(tiers.keys()):
        players = tiers[tier_num]
        label = tier_labels.get(tier_num, f"Tier {tier_num}")

        for pick_num in [1, 2]:
            # Build the dropdown options from the player list
            options = [{"value": name} for name in players]

            requests.append({
                "createItem": {
                    "item": {
                        "title": f"{label} — Pick {pick_num} of 2",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "DROP_DOWN",
                                    "options": options,
                                }
                            }
                        }
                    },
                    "location": {"index": question_index},
                }
            })
            question_index += 1

    # Tiebreaker question
    requests.append({
        "createItem": {
            "item": {
                "title": "Tiebreaker: Predicted Winning Score (relative to par, e.g. -12)",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {
                            "paragraph": False,
                        }
                    }
                }
            },
            "location": {"index": question_index},
        }
    })

    # Step 3: Send all the questions in one batch
    forms_service.forms().batchUpdate(
        formId=form_id,
        body={"requests": requests}
    ).execute()

    # Link the form to a Google Sheet for responses
    print("Linking form to Google Sheet for responses...")
    form_details = forms_service.forms().get(formId=form_id).execute()
    linked_sheet_id = form_details.get("linkedSheetId")

    # If no sheet is auto-linked, we can get responses via Forms API directly
    # The form_id is what we need either way

    # Save form config so the leaderboard app knows where to pull picks from
    config_path = os.path.join(PROJECT_ROOT, "form_config.json")
    import json
    config = {
        "form_id": form_id,
        "linked_sheet_id": linked_sheet_id,
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Config saved to: {config_path}")

    # The form URL
    form_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    print(f"\nForm is ready!")
    print(f"Edit:   https://docs.google.com/forms/d/{form_id}/edit")
    print(f"Share:  {form_url}")

    return form_id, form_url


def main():
    print("Loading tiers from CSV...")
    tiers = load_tiers()

    for tier_num in sorted(tiers.keys()):
        print(f"  Tier {tier_num}: {len(tiers[tier_num])} players")

    print("\nAuthenticating with Google...")
    creds = authenticate()

    print("Creating Google Form...")
    form_id, form_url = create_form(creds, tiers)


if __name__ == "__main__":
    main()
