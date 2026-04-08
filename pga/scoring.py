# scoring.py
# Scoring engine for the 2026 Masters Pool.
# Takes pool picks and live tournament data, then calculates standings.
#
# === Scoring Rules ===
# - All scores are relative to par (e.g. -5 means 5 under par)
# - Cumulative score-to-par across all 10 picks, lowest total wins
# - Missed cut penalty: +5 for round 3, +6 for round 4 = +11 total
# - Placement bonuses (subtracted from total):
#     1st: -15, 2nd: -14, 3rd: -13, 4th: -12, 5th: -11, 6th-10th: -10
# - Tiebreaker: closest prediction to the winning score

import unicodedata


def normalize_name(name):
    """
    Normalize a player name so that accent differences don't break matching.
    e.g. "Ludvig Åberg" and "Ludvig Aberg" both become "ludvig aberg".
    Strips accents and lowercases.
    """
    # Decompose accented characters (e.g. Å → A + combining ring)
    # then strip the combining marks, leaving just the base letter
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower().strip()


# Bonus strokes subtracted for finishing positions
# Key = finishing position, Value = total bonus strokes
PLACEMENT_BONUSES = {
    1: -15,
    2: -14,
    3: -13,
    4: -12,
    5: -11,
    6: -10,
    7: -10,
    8: -10,
    9: -10,
    10: -10,
}

# Missed cut penalty: +5 for round 3, +6 for round 4 = +11 total
MISSED_CUT_PENALTY_R3 = 5
MISSED_CUT_PENALTY_R4 = 6
MISSED_CUT_PENALTY_TOTAL = MISSED_CUT_PENALTY_R3 + MISSED_CUT_PENALTY_R4  # +11

# Withdrawal penalty: +6 for each round not played or finished
WD_PENALTY_PER_ROUND = 6
TOTAL_ROUNDS = 4


def get_placement_bonus(finish_position):
    """
    Return the bonus strokes for a given finishing position.
    Positions 1-10 get bonuses, everyone else gets 0.
    """
    return PLACEMENT_BONUSES.get(finish_position, 0)


def calculate_missed_cut_penalty(made_cut):
    """
    If a player missed the cut, they get +5 for round 3 and +6 for round 4.
    Total penalty = +11. Returns 0 if they made the cut.
    """
    if made_cut:
        return 0
    return MISSED_CUT_PENALTY_TOTAL


def calculate_wd_penalty(wd_round):
    """
    If a player withdraws, they get +6 for each round not played or finished.

    wd_round = the round they withdrew during (1-4).
    That round and all remaining rounds are penalized.
    e.g. WD in round 2 → didn't finish R2, missed R3 & R4 → +6 * 3 = +18

    Returns 0 if wd_round is None (player didn't withdraw).
    """
    if wd_round is None:
        return 0
    rounds_missed = TOTAL_ROUNDS - wd_round + 1
    return WD_PENALTY_PER_ROUND * rounds_missed


def calculate_player_score(player_data):
    """
    Calculate the total pool score for a single picked player.

    player_data should be a dict with:
        - "score": score relative to par (e.g. -5 means 5 under)
        - "made_cut": True/False (None if cut hasn't happened yet)
        - "wd_round": int (1-4) if player withdrew, None otherwise
        - "finish_position": int or None if tournament is still in progress

    Returns a dict with the score breakdown:
        - "score": score relative to par
        - "missed_cut_penalty": +11 if missed, 0 otherwise
        - "wd_penalty": +6 per round not played/finished, 0 otherwise
        - "placement_bonus": negative number for top 10, 0 otherwise
        - "total": score + penalties + bonus
    """
    score = player_data.get("score", 0)

    # WD and missed cut are mutually exclusive — check WD first
    wd_round = player_data.get("wd_round")
    wd_penalty = calculate_wd_penalty(wd_round)

    # Missed cut penalty only applies if they didn't withdraw
    made_cut = player_data.get("made_cut", True)
    mc_penalty = calculate_missed_cut_penalty(made_cut) if wd_round is None else 0

    # Placement bonus only applies if the tournament is over
    finish_position = player_data.get("finish_position")
    bonus = get_placement_bonus(finish_position) if finish_position else 0

    total = score + mc_penalty + wd_penalty + bonus

    return {
        "score": score,
        "missed_cut_penalty": mc_penalty,
        "wd_penalty": wd_penalty,
        "placement_bonus": bonus,
        "total": total,
    }


def calculate_participant_score(picks, tournament_scores):
    """
    Calculate the total pool score for one participant.

    Args:
        picks: list of player names (10 players, 2 per tier)
        tournament_scores: dict mapping player names to their tournament data
            Each entry should have: strokes, made_cut, finish_position

    Returns a dict with:
        - "players": list of per-player score breakdowns
        - "total": sum of all player totals
        - "tiebreaker": the participant's winning score prediction (added separately)
    """
    players = []

    # Build a normalized lookup so "Ludvig Åberg" matches "Ludvig Aberg" etc.
    normalized_scores = {normalize_name(k): v for k, v in tournament_scores.items()}

    for player_name in picks:
        # Try exact match first, then fall back to normalized match
        player_data = tournament_scores.get(player_name)
        if player_data is None:
            player_data = normalized_scores.get(normalize_name(player_name), {})

        score = calculate_player_score(player_data)
        score["name"] = player_name
        players.append(score)

    total = sum(p["total"] for p in players)

    return {
        "players": players,
        "total": total,
    }


def calculate_leaderboard(all_participants, tournament_scores):
    """
    Calculate scores for all participants and return a sorted leaderboard.

    Args:
        all_participants: list of dicts, each with:
            - "name": participant's name
            - "picks": list of 10 player names
            - "tiebreaker": predicted winning score (int)
        tournament_scores: dict mapping player names to tournament data

    Returns a sorted list of participant results (lowest total first).
    Ties are broken by closest tiebreaker to the actual winning score.
    """
    # Get the actual winning score (already relative to par)
    winning_score = None
    for player_name, data in tournament_scores.items():
        if data.get("finish_position") == 1:
            winning_score = data.get("score")  # e.g. -11
            break

    results = []
    for participant in all_participants:
        score = calculate_participant_score(
            participant["picks"], tournament_scores
        )
        score["name"] = participant["name"]
        score["tiebreaker"] = participant.get("tiebreaker")

        # Calculate tiebreaker distance (lower is better)
        if winning_score is not None and score["tiebreaker"] is not None:
            score["tiebreaker_diff"] = abs(score["tiebreaker"] - winning_score)
        else:
            # If tournament isn't over yet, no tiebreaker applies
            score["tiebreaker_diff"] = float("inf")

        results.append(score)

    # Sort by total score (lowest first), then by tiebreaker distance
    results.sort(key=lambda x: (x["total"], x["tiebreaker_diff"]))

    # Add rank to each result
    for i, result in enumerate(results):
        result["rank"] = i + 1

    return results
