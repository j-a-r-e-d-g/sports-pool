# tier_generator.py
# This script pulls odds for the Masters from The Odds API,
# sorts players by their odds to win, and assigns them to tiers.
# Output is a CSV file you can share or import into Google Sheets.
#
# === 2026 Masters Pool Rules ===
# Tiers:       1 (1-10), 2 (11-20), 3 (21-40), 4 (41-70), 5 (71+)
# Picks:       2 per tier = 10 players total per person
# Scoring:     Cumulative strokes across all 10 picks, lowest wins
# Missed cut:  +5 for round 3, +6 for round 4 = +11 total
# Bonuses:     1st: -15, 2nd: -14, 3rd: -13, 4th: -12, 5th: -11, 6th-10th: -10
# Tiebreaker:  Closest prediction to the winning score of the tournament

import requests
import pandas as pd
from dotenv import load_dotenv
import os

# load_dotenv() reads your .env file and makes the API key available
# via os.getenv() — this way the key never has to be written in this file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
API_KEY = os.getenv("ODDS_API_KEY")

# The Odds API endpoint for golf odds
# - sport: golf_masters_tournament_winner is specific to the Masters
# - regions: us means US sportsbooks
# - markets: outrights means tournament winner odds (h2h is for head-to-head matchups)
# - oddsFormat: american means +2000, -110 style odds (standard in the US)
URL = "https://api.the-odds-api.com/v4/sports/golf_masters_tournament_winner/odds"
PARAMS = {
    "apiKey": API_KEY,
    "regions": "us",
    "markets": "outrights",
    "oddsFormat": "american",
}

def fetch_odds():
    """Call the API and return raw data, or exit if something goes wrong."""
    print("Fetching Masters odds from The Odds API...")
    response = requests.get(URL, params=PARAMS)

    # If the API returns an error (bad key, no data, etc), tell us and stop
    if response.status_code != 200:
        print(f"Error fetching odds: {response.status_code} - {response.text}")
        exit()

    data = response.json()

    # The API returns a list of events, each containing bookmakers with their own odds.
    # If the list is empty, the event probably isn't posted yet.
    if not data:
        print("No odds data returned. The Masters market may not be open yet.")
        exit()

    print(f"Got data from {len(data)} bookmakers.")
    return data

def extract_odds(data):
    """
    The API returns odds from multiple bookmakers.
    We'll collect all the odds for each player across all bookmakers,
    then average them to get a fair consensus price.
    """
    # We'll store odds in a dict: { "Player Name": [odds1, odds2, ...] }
    player_odds = {}

    # data is a list of events, each event contains a list of bookmakers
    for event in data:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "outrights":
                    for outcome in market.get("outcomes", []):
                        name = outcome["name"]
                        price = outcome["price"]  # American odds, e.g. +2000 or -110

                        if name not in player_odds:
                            player_odds[name] = []
                        player_odds[name].append(price)

    # Average the odds across bookmakers for each player
    averaged = {}
    for name, odds_list in player_odds.items():
        averaged[name] = sum(odds_list) / len(odds_list)

    return averaged

def american_to_implied_probability(odds):
    """
    Convert American odds to implied probability (0 to 1).
    This is how we sort players — higher probability = shorter odds = better player.

    Example:
      +1000 means bet $100 to win $1000 → implied prob = 100 / (1000 + 100) = ~9%
      -200  means bet $200 to win $100  → implied prob = 200 / (200 + 100) = ~67%
    """
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def assign_tiers(averaged_odds):
    """
    Sort players by implied probability (best odds first),
    then assign them to tiers based on their rank.
    """
    # Build a list of (name, avg_odds, implied_prob) for sorting
    players = []
    for name, odds in averaged_odds.items():
        prob = american_to_implied_probability(odds)
        players.append({"name": name, "avg_odds": round(odds), "implied_prob": prob})

    # Sort best to worst (highest implied probability first)
    players.sort(key=lambda x: x["implied_prob"], reverse=True)

    # Assign tiers based on rank (1-indexed)
    # 5 tiers — pick 2 from each for 10 total players
    tier_map = {
        1: (1, 10),
        2: (11, 20),
        3: (21, 40),
        4: (41, 70),
        5: (71, float("inf")),
    }

    for i, player in enumerate(players):
        rank = i + 1
        player["rank"] = rank

        for tier, (low, high) in tier_map.items():
            if low <= rank <= high:
                player["tier"] = tier
                break

    return players

def save_to_csv(players):
    """Save the tiered player list to a CSV file."""
    df = pd.DataFrame(players, columns=["rank", "name", "avg_odds", "tier"])

    # Format avg_odds nicely: positive odds get a + sign, negative stay as-is
    df["avg_odds"] = df["avg_odds"].apply(lambda x: f"+{x}" if x > 0 else str(x))

    output_path = os.path.join(os.path.dirname(__file__), "masters_tiers.csv")
    df.to_csv(output_path, index=False)
    print(f"\nTiers saved to: {output_path}")
    return df

def main():
    data = fetch_odds()
    averaged_odds = extract_odds(data)
    players = assign_tiers(averaged_odds)
    df = save_to_csv(players)

    # Print a preview grouped by tier
    print("\n--- Masters Tiers Preview ---")
    for tier in range(1, 6):
        tier_players = df[df["tier"] == tier]
        print(f"\nTier {tier} ({len(tier_players)} players — pick 2):")
        print(tier_players[["rank", "name", "avg_odds"]].to_string(index=False))

if __name__ == "__main__":
    main()
