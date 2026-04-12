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
            "wd_round": int or None,
            "finish_position": int or None,
        }

    Two post-processing steps run after initial parsing:
    1. Missed cut detection from linescores (ESPN often leaves status empty)
    2. Finish position assignment with proper tie handling
    """
    scores = {}
    competitor_linescores = {}  # Round-by-round scores for cut detection

    event_status = event.get("status", {}).get("type", {}).get("name", "").upper()

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

            # Store linescores for missed cut detection
            competitor_linescores[name] = competitor.get("linescores", [])

            scores[name] = {
                "score": score,
                "made_cut": made_cut,
                "wd_round": wd_round,
                "finish_position": None,
            }

    # ESPN often doesn't set cut status — detect from R3 linescores instead
    _detect_missed_cuts(scores, competitor_linescores)

    # Compute finish positions with proper tie handling (not ESPN's sequential order)
    # Also assign if all R4 rounds are done — ESPN can be slow to flip STATUS_FINAL
    r4_complete = _all_r4_complete(competitor_linescores)
    if event_status == "STATUS_FINAL" or r4_complete:
        _assign_finish_positions(scores)

    print(f"Parsed scores for {len(scores)} players.")
    return scores


def _all_r4_complete(competitor_linescores):
    """
    Check if all players who made it to R4 have completed their round.
    A completed R4 score is >= 60 strokes (a full round of golf).
    Returns True if every non-zero R4 score is a finished round and
    at least some players have R4 scores.
    """
    r4_values = []
    for linescores in competitor_linescores.values():
        if len(linescores) >= 4:
            r4_val = linescores[3].get("value", 0)
            if r4_val > 0:
                r4_values.append(r4_val)
    return len(r4_values) > 0 and all(v >= 60 for v in r4_values)


def _detect_missed_cuts(scores, competitor_linescores):
    """
    Detect missed cuts from Round 3 linescores.

    ESPN doesn't always populate the cut status field. Once Round 3 is
    complete, we can reliably tell: any player who completed R1 and R2
    but has R3 = 0 missed the cut.

    Waits until ALL made-cut players have finished R3 (every non-zero R3
    score is a full round, >= 60 strokes) to avoid false positives from
    players who simply haven't teed off yet.
    """
    # Gather all non-zero R3 scores
    r3_values = []
    for linescores in competitor_linescores.values():
        if len(linescores) >= 3:
            r3_val = linescores[2].get("value", 0)
            if r3_val > 0:
                r3_values.append(r3_val)

    # R3 must be complete: need scores, and every one must be a finished
    # round (>= 60 strokes). Mid-round values like 14 mean R3 is still
    # in progress — don't flag cuts yet.
    if not r3_values or not all(v >= 60 for v in r3_values):
        return

    cut_count = 0
    for name, linescores in competitor_linescores.items():
        if len(linescores) >= 3:
            r1 = linescores[0].get("value", 0)
            r2 = linescores[1].get("value", 0)
            r3 = linescores[2].get("value", 0)
            # Completed R1 and R2 but no R3 → missed the cut
            if r1 > 0 and r2 > 0 and r3 == 0:
                if name in scores and scores[name]["made_cut"]:
                    scores[name]["made_cut"] = False
                    cut_count += 1

    if cut_count > 0:
        print(f"Detected {cut_count} missed cuts from R3 linescores.")


def _assign_finish_positions(scores):
    """
    Assign finish positions with proper tie handling.

    Players with the same score share the same position:
      scores [-12, -10, -10, -8] → positions [1, 2, 2, 4]

    This matters for bonuses: two players tied for 2nd both get the
    2nd-place bonus (-14), nobody gets 3rd, and the next player is 4th.
    ESPN's "order" field is sequential and doesn't account for ties.
    """
    # Only rank players who finished the tournament (made cut, no WD)
    eligible = [
        (name, data) for name, data in scores.items()
        if data.get("made_cut", True) and data.get("wd_round") is None
    ]
    eligible.sort(key=lambda x: x[1]["score"])

    current_pos = 1
    for i, (name, data) in enumerate(eligible):
        # New score = new position (accounts for ties above)
        if i > 0 and data["score"] > eligible[i - 1][1]["score"]:
            current_pos = i + 1
        scores[name]["finish_position"] = current_pos


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
