# live_scores.py
# Pulls live Masters tournament scores from ESPN's public API.
# Converts the data into the format our scoring engine expects.
#
# ESPN API endpoint for PGA golf scoreboard:
#   https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard
#
# For a specific event (like the Masters), we can filter by event ID.
# The Masters event ID changes each year — this script finds it automatically.

import requests

# ESPN's public golf API — no API key needed
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"


def fetch_scoreboard():
    """
    Fetch the current PGA scoreboard from ESPN.
    Returns the raw JSON response.
    """
    print("Fetching live scores from ESPN...")
    response = requests.get(ESPN_SCOREBOARD_URL)

    if response.status_code != 200:
        print(f"Error fetching scores: {response.status_code}")
        return None

    return response.json()


def find_masters_event(data):
    """
    Look through the ESPN scoreboard data and find the Masters event.
    Returns the event dict, or None if the Masters isn't active.
    """
    for event in data.get("events", []):
        event_name = event.get("name", "").lower()
        # Match "Masters Tournament" or "The Masters"
        if "masters" in event_name:
            print(f"Found Masters event: {event.get('name')}")
            return event

    print("The Masters is not currently on the ESPN scoreboard.")
    return None


def parse_tournament_scores(event):
    """
    Parse an ESPN event into the format our scoring engine expects.

    Returns a dict mapping player names to:
        {
            "score": int (relative to par, e.g. -11),
            "made_cut": bool,
            "finish_position": int or None,
        }
    """
    scores = {}

    # ESPN nests competitors inside competitions
    for competition in event.get("competitions", []):
        for competitor in competition.get("competitors", []):
            athlete = competitor.get("athlete", {})
            name = athlete.get("displayName", "Unknown")

            # "score" in ESPN is the display score like "-9" or "+3" or "E"
            score_str = competitor.get("score", "E")

            # Parse the score string to an int
            if score_str == "E":
                score = 0
            else:
                try:
                    score = int(score_str)
                except (ValueError, TypeError):
                    score = 0

            # Check status — "cut" means missed the cut, "wd" means withdrew
            status = competitor.get("status", {})
            status_type = status.get("type", {}).get("name", "").lower()
            made_cut = status_type not in ("cut", "missed_cut", "mc")

            # Detect withdrawal and figure out which round they withdrew in
            wd_round = None
            if status_type == "wd":
                # ESPN tracks the current period (round) the player was in
                period = status.get("period", 0)
                # Clamp to valid range 1-4
                wd_round = max(1, min(4, period)) if period >= 1 else 1

            # Finish position (only set if tournament is complete or player is done)
            # ESPN uses "order" for current position on the leaderboard
            position = competitor.get("order")
            # Only treat as final finish position if the event is complete
            # Case-insensitive check for safety
            event_status = event.get("status", {}).get("type", {}).get("name", "").upper()
            if event_status == "STATUS_FINAL":
                finish_position = position if position and position > 0 else None
            else:
                finish_position = None

            scores[name] = {
                "score": score,
                "made_cut": made_cut,
                "wd_round": wd_round,
                "finish_position": finish_position,
            }

    print(f"Parsed scores for {len(scores)} players.")
    return scores


def get_live_masters_scores():
    """
    Main function — fetches the ESPN scoreboard, finds the Masters,
    and returns parsed scores in our scoring engine format.

    Returns:
        - dict of player scores if the Masters is live
        - None if the Masters isn't on the scoreboard
    """
    data = fetch_scoreboard()
    if not data:
        return None

    event = find_masters_event(data)
    if not event:
        return None

    return parse_tournament_scores(event)


def get_current_tournament():
    """
    Fetch whatever PGA tournament is currently on the ESPN scoreboard.
    Returns a tuple of (event_name, scores_dict) or (None, None) if nothing is active.
    """
    data = fetch_scoreboard()
    if not data:
        return None, None

    events = data.get("events", [])
    if not events:
        return None, None

    # Grab the first event on the scoreboard
    event = events[0]
    event_name = event.get("name", "Unknown Event")
    print(f"Found current event: {event_name}")
    scores = parse_tournament_scores(event)
    return event_name, scores


# Quick test: run this directly to see what's on the scoreboard
if __name__ == "__main__":
    data = fetch_scoreboard()
    if data:
        print(f"\nEvents on ESPN scoreboard:")
        for event in data.get("events", []):
            print(f"  - {event.get('name')}")

        masters = find_masters_event(data)
        if masters:
            scores = parse_tournament_scores(masters)
            # Show top 10 by score
            sorted_players = sorted(scores.items(), key=lambda x: x[1]["score"])
            print(f"\nTop 10 on the leaderboard:")
            for i, (name, data) in enumerate(sorted_players[:10]):
                score = data["score"]
                sign = "+" if score > 0 else ""
                cut = " (MC)" if not data["made_cut"] else ""
                print(f"  {i+1}. {name}: {sign}{score}{cut}")
        else:
            print("\nNo Masters event found — showing current PGA event:")
            for event in data.get("events", []):
                scores = parse_tournament_scores(event)
                sorted_players = sorted(scores.items(), key=lambda x: x[1]["score"])
                print(f"\n{event.get('name')} — Top 10:")
                for i, (name, d) in enumerate(sorted_players[:10]):
                    score = d["score"]
                    sign = "+" if score > 0 else ""
                    print(f"  {i+1}. {name}: {sign}{score}")
                break
