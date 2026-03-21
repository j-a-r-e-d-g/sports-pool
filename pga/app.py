# app.py
# Streamlit web app for the 2026 Masters Pool leaderboard.
# Run with: streamlit run pga/app.py
#
# Pulls picks from Google Form responses when available,
# falls back to sample data for testing.
#
# Auto-refreshes every 60 minutes during tournament hours (8am–8pm ET).
# Pauses overnight when no golf is being played.

import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from scoring import calculate_leaderboard
from sample_data import SAMPLE_PARTICIPANTS, SAMPLE_TOURNAMENT_SCORES

# ---------- Auto-Refresh Config ----------
# Tournament hours: 8am–8pm Eastern Time
TOURNAMENT_TZ = ZoneInfo("America/New_York")
TOURNAMENT_START_HOUR = 8   # 8am ET
TOURNAMENT_END_HOUR = 20    # 8pm ET
REFRESH_INTERVAL_SEC = 3600  # 60 minutes


def is_tournament_hours():
    """Check if we're within tournament hours (8am–8pm ET)."""
    now_et = datetime.now(TOURNAMENT_TZ)
    return TOURNAMENT_START_HOUR <= now_et.hour < TOURNAMENT_END_HOUR


def get_last_refresh_str():
    """Return a human-readable timestamp of the current refresh."""
    now_et = datetime.now(TOURNAMENT_TZ)
    return now_et.strftime("%I:%M %p ET")


# ---------- Data Loading (cached to avoid redundant API calls) ----------
@st.cache_data(ttl=REFRESH_INTERVAL_SEC)
def load_picks():
    """Load picks from Google Form responses, cached for 60 min."""
    try:
        from sheets_reader import fetch_picks
        return fetch_picks()
    except Exception:
        return []


@st.cache_data(ttl=REFRESH_INTERVAL_SEC)
def load_live_scores():
    """Load live Masters scores from ESPN, cached for 60 min."""
    try:
        from live_scores import get_live_masters_scores
        return get_live_masters_scores()
    except Exception:
        return None


real_picks = load_picks()
live_scores = load_live_scores()

# Auto-refresh the browser page every 60 minutes during tournament hours
# This ensures anyone with the page open gets fresh scores automatically
if is_tournament_hours():
    st.html(f'<meta http-equiv="refresh" content="{REFRESH_INTERVAL_SEC}">')


def format_score(score):
    """Format a score relative to par: -5, E, +3, etc."""
    if score == 0:
        return "E"
    return f"{score:+d}"


# ---------- Page Config ----------
st.set_page_config(
    page_title="2026 Masters Pool",
    page_icon="⛳",
    layout="wide",
)

st.title("⛳ 2026 Masters Pool Leaderboard")
st.caption(
    "Scoring: cumulative to-par · missed cut +5 R3, +6 R4 (= +11 total) · "
    "top 10 bonus: -10 · top 5 placement: 1st -15, 2nd -14, 3rd -13, 4th -12, 5th -11"
)

# ---------- Data Source ----------
# Use real picks from Google Form if available, otherwise sample data
if real_picks:
    participants = real_picks
    st.success(f"Loaded {len(participants)} picks from Google Form responses")
else:
    participants = SAMPLE_PARTICIPANTS
    st.warning("Using sample data — no form responses found yet")

# Use live scores from ESPN if the Masters is active, otherwise sample data
if live_scores:
    tournament_scores = live_scores
    st.success("Live Masters scores from ESPN")
else:
    tournament_scores = SAMPLE_TOURNAMENT_SCORES
    st.info("Masters not live yet — using sample tournament data")

# Show refresh status
refresh_time = get_last_refresh_str()
if is_tournament_hours():
    st.caption(f"Last updated: {refresh_time} · Auto-refreshing every 60 min during tournament hours")
else:
    st.caption(f"Last updated: {refresh_time} · Auto-refresh paused (outside tournament hours 8am–8pm ET)")

# ---------- Calculate Standings ----------
leaderboard = calculate_leaderboard(participants, tournament_scores)

# Check if the tournament has a winner (for tiebreaker display)
winning_score = None
winner_name = None
for player_name, data in tournament_scores.items():
    if data.get("finish_position") == 1:
        winning_score = data["score"]
        winner_name = player_name
        break

# ---------- Leaderboard Table ----------
st.subheader("Pool Standings")

# Build the main leaderboard dataframe
leaderboard_rows = []
for entry in leaderboard:
    row = {
        "Rank": entry["rank"],
        "Participant": entry["name"],
        "Total": format_score(entry["total"]),
        "Tiebreaker Guess": format_score(entry["tiebreaker"]),
    }
    # Show tiebreaker diff only if tournament is over
    if winning_score is not None:
        row["Tiebreaker Diff"] = entry["tiebreaker_diff"]
    leaderboard_rows.append(row)

df_leaderboard = pd.DataFrame(leaderboard_rows)
st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)

# Show winning score if tournament is over
if winning_score is not None:
    st.info(f"🏆 **{winner_name}** won the Masters at **{format_score(winning_score)}**")

# ---------- Participant Detail Cards ----------
st.subheader("Detailed Breakdowns")

# Let users pick which participant to view, or show all
selected = st.selectbox(
    "Select participant",
    ["All"] + [entry["name"] for entry in leaderboard],
)

entries_to_show = leaderboard if selected == "All" else [
    e for e in leaderboard if e["name"] == selected
]

for entry in entries_to_show:
    with st.expander(
        f"#{entry['rank']} — {entry['name']} ({format_score(entry['total'])})",
        expanded=(selected != "All"),
    ):
        # Build a table of their 10 picks with score breakdowns
        player_rows = []
        for player in entry["players"]:
            player_rows.append({
                "Player": player["name"],
                "Score": format_score(player["score"]),
                "MC Penalty": f"+{player['missed_cut_penalty']}" if player["missed_cut_penalty"] > 0 else "—",
                "Bonus": player["placement_bonus"] if player["placement_bonus"] != 0 else "—",
                "Player Total": format_score(player["total"]),
            })

        df_players = pd.DataFrame(player_rows)
        st.dataframe(df_players, use_container_width=True, hide_index=True)

        # Summary line
        total_scores = sum(p["score"] for p in entry["players"])
        total_penalties = sum(p["missed_cut_penalty"] for p in entry["players"])
        total_bonuses = sum(p["placement_bonus"] for p in entry["players"])
        st.markdown(
            f"**Score to Par:** {format_score(total_scores)} · "
            f"**Penalties:** +{total_penalties} · "
            f"**Bonuses:** {total_bonuses} · "
            f"**Net Total:** {format_score(entry['total'])}"
        )
