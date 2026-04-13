# app.py
# Streamlit web app for the PGA pool leaderboard.
# Run with: streamlit run pga/app.py
#
# Augusta National themed — white scoreboards, Masters green, red for under par.
# Tabs: Pool Standings | Player Breakdowns | Tournament Leaderboard | Rules
#
# Loads picks from Postgres for DB tournaments, falls back to Google Sheets
# for the legacy Masters 2026 pool.
#
# Auto-refreshes every 15 minutes during tournament hours (8am–8pm ET).

import sys
import os

# Ensure the pga/ directory is on the Python path so imports work
# whether running locally (cd pga && streamlit run app.py) or from
# the repo root (Streamlit Cloud runs: streamlit run pga/app.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env for local development (DATABASE_URL)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from scoring import calculate_leaderboard
from db import init_db, list_tournaments, get_tiers, get_entries
from themes import get_theme, theme_css, shared_styles, header_html

# Ensure database tables exist
init_db()

# ---------- Page Config (must be first Streamlit call) ----------
st.set_page_config(
    page_title="PGA Pool",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Theme ----------
# Theme is applied dynamically after tournament selection.
# A default is used initially so the page doesn't flash white.
from themes import DEFAULT_THEME
_current_theme = DEFAULT_THEME
st.markdown(theme_css(_current_theme), unsafe_allow_html=True)
SHARED_STYLES = shared_styles(_current_theme)

# ---------- Auto-Refresh Config ----------
TOURNAMENT_TZ = ZoneInfo("America/New_York")
TOURNAMENT_START_HOUR = 8
TOURNAMENT_END_HOUR = 20
REFRESH_INTERVAL_SEC = 900  # 15 minutes


def is_tournament_hours():
    """Check if we're within tournament hours (8am-8pm ET)."""
    now_et = datetime.now(TOURNAMENT_TZ)
    return TOURNAMENT_START_HOUR <= now_et.hour < TOURNAMENT_END_HOUR


def get_last_refresh_str():
    """Return a human-readable timestamp of the current refresh."""
    now_et = datetime.now(TOURNAMENT_TZ)
    return now_et.strftime("%I:%M %p ET")


# ---------- Score Formatting Helpers ----------
def format_score(score):
    """Format a score relative to par: -5, E, +3, etc."""
    if score == 0:
        return "E"
    return f"{score:+d}"


def score_html(score):
    """Return score wrapped in a colored span — red for under par."""
    text = format_score(score)
    if score < 0:
        return f'<span class="score-under">{text}</span>'
    elif score > 0:
        return f'<span class="score-over">{text}</span>'
    else:
        return f'<span class="score-even">{text}</span>'


def rank_html(rank):
    """Return a styled rank badge."""
    if rank == 1:
        cls = "rank-1"
    elif rank == 2:
        cls = "rank-2"
    elif rank == 3:
        cls = "rank-3"
    else:
        cls = "rank-other"
    return f'<span class="rank-badge {cls}">{rank}</span>'


# ---------- Data Loading ----------
@st.cache_data(ttl=REFRESH_INTERVAL_SEC)
def load_picks_from_db(tournament_id):
    """Load picks from Postgres for the given tournament."""
    try:
        return get_entries(tournament_id)
    except Exception as e:
        st.error(f"Error loading picks: {e}")
        return []


@st.cache_data(ttl=REFRESH_INTERVAL_SEC)
def load_picks_from_sheets():
    """Legacy: load picks from Google Form responses (Masters 2026)."""
    try:
        from sheets_reader import fetch_picks
        return fetch_picks()
    except Exception as e:
        st.error(f"Error loading picks: {e}")
        return []


@st.cache_data(ttl=REFRESH_INTERVAL_SEC)
def load_espn_scores(espn_event_name):
    """Load live scores from ESPN, matching by event name."""
    try:
        from live_scores import fetch_scoreboard, parse_tournament_scores
        data = fetch_scoreboard()
        if not data:
            return None
        for event in data.get("events", []):
            if espn_event_name and espn_event_name.lower() in event.get("name", "").lower():
                return parse_tournament_scores(event)
        # Fallback: try the Masters-specific matcher
        from live_scores import get_live_masters_scores
        return get_live_masters_scores()
    except Exception:
        return None


@st.cache_data(ttl=REFRESH_INTERVAL_SEC)
def load_current_tournament():
    """Load whatever PGA event is currently on ESPN, for the Tournament Leaderboard tab."""
    try:
        from live_scores import get_current_tournament
        return get_current_tournament()
    except Exception:
        return None, None


# ---------- Tournament Selection ----------
# Show active (non-archived) DB tournaments on the leaderboard.
# Final tournaments live in the Archives page.
db_tournaments = list_tournaments()
active_db = [t for t in db_tournaments if t["status"] in ("open", "locked", "live")]

# Build tournament options
tournament_options = []
for t in active_db:
    tournament_options.append({"label": t["name"], "db": t})
# If no active tournaments, show a placeholder
if not active_db:
    tournament_options.append({"label": "No active tournament", "db": None})

if len(tournament_options) > 1:
    selected_idx = st.selectbox(
        "Tournament",
        range(len(tournament_options)),
        format_func=lambda i: tournament_options[i]["label"],
    )
    active_tournament = tournament_options[selected_idx]
else:
    active_tournament = tournament_options[0]

# Load data based on source
db_tourney = active_tournament.get("db")
if db_tourney:
    real_picks = load_picks_from_db(db_tourney["id"])
    espn_name = db_tourney.get("espn_event_name", "")
    live_scores = load_espn_scores(espn_name)
    pool_tiers = get_tiers(db_tourney["id"])
else:
    # Legacy Masters path
    real_picks = load_picks_from_sheets()
    live_scores = load_espn_scores("Masters")
    pool_tiers = None

# Apply tournament theme
_current_theme = get_theme(db_tourney)
st.markdown(theme_css(_current_theme), unsafe_allow_html=True)
SHARED_STYLES = shared_styles(_current_theme)

current_event_name, current_event_scores = load_current_tournament()

# Auto-refresh during tournament hours
if is_tournament_hours():
    st.html(f'<meta http-equiv="refresh" content="{REFRESH_INTERVAL_SEC}">')

# ---------- Data Source ----------
if real_picks:
    participants = real_picks
    data_source_picks = f"{len(participants)} entries"
else:
    participants = []
    data_source_picks = "No entries yet"

if live_scores:
    tournament_scores = live_scores
    data_source_scores = "Live from ESPN"
else:
    tournament_scores = {}
    data_source_scores = "Not live yet"

# ---------- Calculate Standings ----------
leaderboard = calculate_leaderboard(participants, tournament_scores)

# Check for tournament winner
winning_score = None
winner_name = None
for player_name, data in tournament_scores.items():
    if data.get("finish_position") == 1:
        winning_score = data["score"]
        winner_name = player_name
        break

# ---------- Header ----------
refresh_time = get_last_refresh_str()
if is_tournament_hours():
    refresh_text = f"Last updated: {refresh_time} &middot; Auto-refreshing every 15 min"
else:
    refresh_text = f"Last updated: {refresh_time} &middot; Refresh paused (outside 8am&ndash;8pm ET)"

_title = db_tourney["name"].upper() + " POOL" if db_tourney else "PGA POOL"
_subtitle = "PGA Tour &middot; 2026"
st.html(header_html(_current_theme, _title, _subtitle) + """
<div style="text-align: center; font-size: 0.85rem; color: #c0c0b0; padding: 0.5rem;">
    %s &middot; Picks: %s &middot; Scores: %s
</div>
""" % (refresh_text, data_source_picks, data_source_scores))

# Winner banner if tournament is over
if winning_score is not None:
    _tourney_name = db_tourney["name"] if db_tourney else "the Masters"
    st.html(SHARED_STYLES + """
    <div class="winner-banner">
        <span>&#127942; %s wins %s at %s &#127942;</span>
    </div>
    """ % (winner_name, _tourney_name, format_score(winning_score)))

# ---------- Tabs ----------
tab_standings, tab_breakdowns, tab_tournament, tab_rules = st.tabs([
    "Pool Standings", "Player Breakdowns", "Tournament Leaderboard", "Scoring Rules"
])

# ==================== TAB 1: POOL STANDINGS ====================
with tab_standings:
    rows_html = ""
    for entry in leaderboard:
        row_class = ' class="leader-row"' if entry["rank"] == 1 else ""
        tb_text = format_score(entry["tiebreaker"]) if entry["tiebreaker"] is not None else "&mdash;"

        tb_diff_cell = ""
        if winning_score is not None:
            diff = entry["tiebreaker_diff"]
            tb_diff_cell = f"<td>{diff}</td>"

        rows_html += f"""
        <tr{row_class}>
            <td>{rank_html(entry['rank'])}</td>
            <td>{entry['name']}</td>
            <td>{score_html(entry['total'])}</td>
            <td>{tb_text}</td>
            {tb_diff_cell}
        </tr>"""

    tb_diff_header = "<th>TB Diff</th>" if winning_score is not None else ""

    # Calculate height based on number of rows (header + rows + padding)
    standings_height = 80 + len(leaderboard) * 42

    st.html(f"""
    {SHARED_STYLES}
    <div class="scoreboard">
        <h3>Pool Standings</h3>
        <table class="leaderboard-table">
            <thead>
                <tr>
                    <th>Pos</th>
                    <th>Name</th>
                    <th>Total</th>
                    <th>Tiebreaker</th>
                    {tb_diff_header}
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """)


# ==================== TAB 2: PLAYER BREAKDOWNS ====================
with tab_breakdowns:
    selected = st.selectbox(
        "Select participant",
        ["All"] + [entry["name"] for entry in leaderboard],
        key="breakdown_select",
    )

    entries_to_show = leaderboard if selected == "All" else [
        e for e in leaderboard if e["name"] == selected
    ]

    for entry in entries_to_show:
        player_rows_html = ""
        for player in entry["players"]:
            mc = player["missed_cut_penalty"]
            wd = player.get("wd_penalty", 0)

            if wd > 0:
                penalty_str = f'<span class="score-wd">+{wd} WD</span>'
            elif mc > 0:
                penalty_str = f'<span class="score-mc">+{mc} MC</span>'
            else:
                penalty_str = "&mdash;"

            bonus = player["placement_bonus"]
            bonus_str = str(bonus) if bonus != 0 else "&mdash;"

            player_rows_html += f"""
            <tr>
                <td>{player['name']}</td>
                <td>{score_html(player['score'])}</td>
                <td>{penalty_str}</td>
                <td>{bonus_str}</td>
                <td>{score_html(player['total'])}</td>
            </tr>"""

        total_scores = sum(p["score"] for p in entry["players"])
        total_penalties = sum(p["missed_cut_penalty"] + p.get("wd_penalty", 0) for p in entry["players"])
        total_bonuses = sum(p["placement_bonus"] for p in entry["players"])

        st.html(f"""
        {SHARED_STYLES}
        <div class="detail-card">
            <h4>{rank_html(entry['rank'])} &nbsp; {entry['name']} &mdash; {score_html(entry['total'])}</h4>
            <table class="detail-table">
                <thead>
                    <tr>
                        <th>Player</th>
                        <th>Score</th>
                        <th>Penalty</th>
                        <th>Bonus</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    {player_rows_html}
                </tbody>
            </table>
            <div class="summary-line">
                Score: {score_html(total_scores)} &middot;
                Penalties: +{total_penalties} &middot;
                Bonuses: {total_bonuses} &middot;
                <strong>Net: {score_html(entry['total'])}</strong>
            </div>
        </div>
        """)


# ==================== TAB 3: TOURNAMENT LEADERBOARD ====================
with tab_tournament:
    # Use live ESPN data: current tournament scores if available
    if live_scores:
        tourney_title = db_tourney["name"] if db_tourney else "Masters Tournament"
        tourney_data = live_scores
    elif current_event_scores:
        tourney_title = f"{current_event_name} (Live from ESPN)"
        tourney_data = current_event_scores
    else:
        tourney_title = "Tournament Leaderboard"
        tourney_data = {}

    # Build lookup: which players were picked by whom (and what tier)
    # normalize names for matching across form picks vs ESPN names
    from scoring import normalize_name, get_placement_bonus

    pick_lookup = {}  # normalized_name -> [(participant, tier_label), ...]
    if participants and pool_tiers:
        for entry in participants:
            for i, player_name in enumerate(entry.get("picks", [])):
                if not player_name:
                    continue
                # Figure out which tier this pick belongs to
                picks_so_far = 0
                tier_label = ""
                for tier in pool_tiers:
                    if picks_so_far <= i < picks_so_far + tier["picks_required"]:
                        tier_label = tier["label"]
                        break
                    picks_so_far += tier["picks_required"]
                norm = normalize_name(player_name)
                pick_lookup.setdefault(norm, []).append((entry["name"], tier_label))
    elif participants:
        # Legacy Masters: infer tiers from pick position (2 per tier)
        tier_labels = ["Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"]
        for entry in participants:
            for i, player_name in enumerate(entry.get("picks", [])):
                if not player_name:
                    continue
                tier_label = tier_labels[i // 2] if i // 2 < len(tier_labels) else ""
                norm = normalize_name(player_name)
                pick_lookup.setdefault(norm, []).append((entry["name"], tier_label))

    sorted_players = sorted(
        tourney_data.items(),
        key=lambda x: (x[1]["score"], x[1].get("finish_position") or 999),
    )

    tourney_rows_html = ""
    for i, (name, data) in enumerate(sorted_players):
        score = data["score"]
        made_cut = data.get("made_cut", True)
        wd_round = data.get("wd_round")
        pos = data.get("finish_position")

        pos_str = str(pos) if pos else str(i + 1)

        if wd_round:
            status = f'<span class="score-wd">WD R{wd_round}</span>'
        elif not made_cut:
            status = '<span class="score-mc">MC</span>'
        else:
            status = ""

        # Bonus column
        bonus = get_placement_bonus(pos) if pos else 0
        if bonus < 0:
            bonus_cell = f'<span class="bonus-badge">{bonus}</span>'
        else:
            bonus_cell = '<span class="bonus-none">&mdash;</span>'

        # Pool picks column — who picked this player and from what tier
        norm_name = normalize_name(name)
        pickers = pick_lookup.get(norm_name, [])
        if pickers:
            picker_tags = ""
            for participant, tier_label in pickers:
                tier_html = f'<span class="tier-tag">{tier_label}</span>' if tier_label else ""
                picker_tags += f'{tier_html}<span class="picked-tag">{participant}</span> '
            picked_cell = picker_tags
        else:
            picked_cell = ""

        tourney_rows_html += f"""
        <tr>
            <td>{pos_str}</td>
            <td>{name}</td>
            <td>{score_html(score)}</td>
            <td>{bonus_cell}</td>
            <td>{status}</td>
            <td>{picked_cell}</td>
        </tr>"""

    st.html(f"""
    {SHARED_STYLES}
    <div class="scoreboard">
        <h3>{tourney_title} Leaderboard</h3>
        <table class="leaderboard-table">
            <thead>
                <tr>
                    <th>Pos</th>
                    <th>Player</th>
                    <th>Score</th>
                    <th>Bonus</th>
                    <th>Status</th>
                    <th>Picked By</th>
                </tr>
            </thead>
            <tbody>
                {tourney_rows_html}
            </tbody>
        </table>
    </div>
    """)


# ==================== TAB 4: SCORING RULES ====================
with tab_rules:
    # Build tier rows
    tier_rows_html = ""
    if pool_tiers:
        for t in pool_tiers:
            rank_max = t["rank_max"] if t["rank_max"] else "+"
            tier_rows_html += (
                "<tr><td>%s</td><td>%s &ndash; %s</td><td>%s</td></tr>"
                % (t["label"], t["rank_min"], rank_max, t["picks_required"])
            )

    # Pull rules from tournament config
    rules = db_tourney.get("rules", {}) if db_tourney else {}
    r_buy_in = rules.get("buy_in", 10)
    r_p1 = rules.get("payout_1st", 100)
    r_p2 = rules.get("payout_2nd", 50)
    r_p3 = rules.get("payout_3rd", 20)
    r_mc_r3 = rules.get("mc_r3", 5)
    r_mc_r4 = rules.get("mc_r4", 6)
    r_mc_total = r_mc_r3 + r_mc_r4
    r_wd = rules.get("wd_penalty", 15)
    r_bonuses = rules.get("bonuses", {"1st": 15, "2nd": 14, "3rd": 13, "4th": 12, "5th": 11})
    r_top10 = rules.get("top10_bonus", 10)
    r_notes = rules.get("notes", "")

    # Build bonus rows
    bonus_rows_html = ""
    for pos in ["1st", "2nd", "3rd", "4th", "5th"]:
        val = r_bonuses.get(pos, 0)
        if val > 0:
            bonus_rows_html += "<tr><td>%s</td><td><strong>-%d</strong></td></tr>" % (pos, val)
    if r_top10 > 0:
        bonus_rows_html += "<tr><td>6th &ndash; 10th</td><td><strong>-%d</strong></td></tr>" % r_top10

    notes_html = ""
    if r_notes:
        notes_html = "<h3>Special Rules</h3><p>%s</p>" % r_notes

    st.html("""
    %s
    <div class="rules-card">
        <h3>Payouts</h3>
        <p><strong>$%d buy-in</strong> &middot; 1st: $%d &middot; 2nd: $%d &middot; 3rd: $%d</p>

        <h3>Pool Format</h3>
        <p>Pick players from each tier. Your score is the
        cumulative to-par total across all your picks. <strong>Lowest score wins.</strong></p>
        <table>
            <tr><th>Tier</th><th>Players Ranked</th><th>Picks</th></tr>
            %s
        </table>

        <h3>Missed Cut Penalty</h3>
        <p>If one of your players misses the cut, their score gets a penalty added:</p>
        <table>
            <tr><th>Round</th><th>Penalty</th></tr>
            <tr><td>Round 3</td><td>+%d</td></tr>
            <tr><td>Round 4</td><td>+%d</td></tr>
            <tr><td><strong>Total</strong></td><td><strong>+%d</strong></td></tr>
        </table>

        <h3>Withdrawal Penalty</h3>
        <p>If a player withdraws, they receive <strong>+%d strokes penalty</strong>.</p>

        <h3>Placement Bonuses</h3>
        <p>Players finishing in the <strong>top 10</strong> earn a bonus (subtracted from your total):</p>
        <table>
            <tr><th>Finish</th><th>Bonus</th></tr>
            %s
        </table>

        <h3>Tiebreaker</h3>
        <p>If two or more participants are tied on total score, the tiebreaker is
        <strong>closest prediction to the winning score</strong> of the tournament.</p>

        %s
    </div>
    """ % (SHARED_STYLES, r_buy_in, r_p1, r_p2, r_p3,
           tier_rows_html, r_mc_r3, r_mc_r4, r_mc_total,
           r_wd, bonus_rows_html, notes_html))
