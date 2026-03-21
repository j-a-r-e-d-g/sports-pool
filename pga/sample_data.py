# sample_data.py
# Mock data for testing the leaderboard app before the actual tournament.
# Includes fake picks for 4 participants and simulated tournament scores.

# Sample pool participants with their picks (2 per tier) and tiebreaker prediction
SAMPLE_PARTICIPANTS = [
    {
        "name": "Jared",
        "picks": [
            # Tier 1 (1-10)
            "Scottie Scheffler", "Rory McIlroy",
            # Tier 2 (11-20)
            "Hideki Matsuyama", "Jordan Spieth",
            # Tier 3 (21-40)
            "Shane Lowry", "Corey Conners",
            # Tier 4 (41-70)
            "Keegan Bradley", "Dustin Johnson",
            # Tier 5 (71+)
            "Tiger Woods", "Phil Mickelson",
        ],
        "tiebreaker": -12,  # Predicts winning score of -12
    },
    {
        "name": "Mike",
        "picks": [
            "Xander Schauffele", "Ludvig Aberg",
            "Brooks Koepka", "Viktor Hovland",
            "Patrick Cantlay", "Min Woo Lee",
            "Daniel Berger", "Wyndham Clark",
            "Davis Thompson", "Bubba Watson",
        ],
        "tiebreaker": -10,
    },
    {
        "name": "Sarah",
        "picks": [
            "Jon Rahm", "Tommy Fleetwood",
            "Robert Macintyre", "Tyrrell Hatton",
            "Joaquin Niemann", "Sahith Theegala",
            "Marco Penge", "Tony Finau",
            "Max Greyserman", "Denny McCarthy",
        ],
        "tiebreaker": -14,
    },
    {
        "name": "Dave",
        "picks": [
            "Bryson DeChambeau", "Collin Morikawa",
            "Patrick Reed", "Justin Thomas",
            "Akshay Bhatia", "Rickie Fowler",
            "Harris English", "Sergio Garcia",
            "Billy Horschel", "Fred Couples",
        ],
        "tiebreaker": -8,
    },
]

# Simulated tournament scores after all 4 rounds
# Scores are relative to par (Augusta par = 72/round)
# Scheffler wins at -11, a few guys miss the cut
SAMPLE_TOURNAMENT_SCORES = {
    # === Top finishers (score = to par after 4 rounds) ===
    "Scottie Scheffler":    {"score": -11, "made_cut": True, "finish_position": 1},
    "Xander Schauffele":    {"score": -9,  "made_cut": True, "finish_position": 2},
    "Rory McIlroy":         {"score": -8,  "made_cut": True, "finish_position": 3},
    "Bryson DeChambeau":    {"score": -8,  "made_cut": True, "finish_position": 3},   # T3
    "Collin Morikawa":      {"score": -7,  "made_cut": True, "finish_position": 5},
    "Jon Rahm":             {"score": -6,  "made_cut": True, "finish_position": 7},
    "Ludvig Aberg":         {"score": -5,  "made_cut": True, "finish_position": 9},

    # === Made the cut, mid-pack ===
    "Tommy Fleetwood":      {"score": -4,  "made_cut": True, "finish_position": 12},
    "Patrick Cantlay":      {"score": -4,  "made_cut": True, "finish_position": 12},
    "Hideki Matsuyama":     {"score": -3,  "made_cut": True, "finish_position": 15},
    "Shane Lowry":          {"score": -3,  "made_cut": True, "finish_position": 15},
    "Brooks Koepka":        {"score": -2,  "made_cut": True, "finish_position": 18},
    "Robert Macintyre":     {"score": -2,  "made_cut": True, "finish_position": 18},
    "Min Woo Lee":          {"score": -2,  "made_cut": True, "finish_position": 18},
    "Jordan Spieth":        {"score": -1,  "made_cut": True, "finish_position": 22},
    "Corey Conners":        {"score": -1,  "made_cut": True, "finish_position": 22},
    "Viktor Hovland":       {"score":  0,  "made_cut": True, "finish_position": 25},
    "Justin Thomas":        {"score":  0,  "made_cut": True, "finish_position": 25},
    "Joaquin Niemann":      {"score":  0,  "made_cut": True, "finish_position": 25},
    "Tyrrell Hatton":       {"score": +1,  "made_cut": True, "finish_position": 30},
    "Sahith Theegala":      {"score": +1,  "made_cut": True, "finish_position": 30},
    "Daniel Berger":        {"score": +1,  "made_cut": True, "finish_position": 30},
    "Akshay Bhatia":        {"score": +2,  "made_cut": True, "finish_position": 35},
    "Patrick Reed":         {"score": +2,  "made_cut": True, "finish_position": 35},
    "Wyndham Clark":        {"score": +2,  "made_cut": True, "finish_position": 35},
    "Tony Finau":           {"score": +2,  "made_cut": True, "finish_position": 35},
    "Rickie Fowler":        {"score": +3,  "made_cut": True, "finish_position": 40},
    "Keegan Bradley":       {"score": +3,  "made_cut": True, "finish_position": 40},
    "Harris English":       {"score": +3,  "made_cut": True, "finish_position": 40},
    "Marco Penge":          {"score": +4,  "made_cut": True, "finish_position": 45},
    "Davis Thompson":       {"score": +4,  "made_cut": True, "finish_position": 45},
    "Max Greyserman":       {"score": +5,  "made_cut": True, "finish_position": 48},

    # === Missed the cut — score is to par after rounds 1 & 2 only ===
    # Penalty of +11 gets added on top by the scoring engine
    "Denny McCarthy":       {"score": +5,  "made_cut": False, "finish_position": None},
    "Dustin Johnson":       {"score": +6,  "made_cut": False, "finish_position": None},
    "Billy Horschel":       {"score": +7,  "made_cut": False, "finish_position": None},
    "Tiger Woods":          {"score": +8,  "made_cut": False, "finish_position": None},
    "Sergio Garcia":        {"score": +9,  "made_cut": False, "finish_position": None},
    "Phil Mickelson":       {"score": +10, "made_cut": False, "finish_position": None},
    "Bubba Watson":         {"score": +12, "made_cut": False, "finish_position": None},
    "Fred Couples":         {"score": +14, "made_cut": False, "finish_position": None},
}
