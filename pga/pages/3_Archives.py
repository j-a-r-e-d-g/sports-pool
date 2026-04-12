# Archives page — view final results from past pool tournaments.

import sys
import os

_pga_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _pga_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_pga_dir, "..", ".env"))

import streamlit as st
from db import init_db, get_archived_tournaments, get_results

st.set_page_config(page_title="Pool Archives", page_icon="⛳", layout="wide")

init_db()

# ---------- Theme ----------
THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600;700&display=swap');
    .stApp { background-color: #006747; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

# ---------- Shared Styles for HTML blocks ----------
SHARED_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600;700&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

    .score-under { color: #CE1141; font-weight: 700; }
    .score-over { color: #1a1a1a; font-weight: 600; }
    .score-even { color: #1a1a1a; font-weight: 600; }
    .score-mc { color: #8B4513; font-style: italic; }

    .rank-badge {
        display: inline-block;
        width: 28px; height: 28px; line-height: 28px;
        text-align: center; border-radius: 50%;
        font-weight: 700; font-size: 0.85rem;
    }
    .rank-1 { background-color: #FFD700; color: #006747; }
    .rank-2 { background-color: #C0C0C0; color: #333; }
    .rank-3 { background-color: #CD7F32; color: #fff; }
    .rank-other { background-color: #e8e8e0; color: #333; }

    .scoreboard {
        background-color: #FFFEF7; border-radius: 8px;
        padding: 1.2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3); color: #1a1a1a;
    }
    .scoreboard h3 {
        color: #006747; font-family: 'EB Garamond', Georgia, serif;
        font-size: 1.3rem; border-bottom: 2px solid #006747;
        padding-bottom: 0.4rem; margin-bottom: 0.8rem;
    }
    .leaderboard-table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
    .leaderboard-table th {
        background-color: #006747; color: #FFD700;
        padding: 0.6rem 0.8rem; text-align: left;
        font-family: 'EB Garamond', Georgia, serif; font-size: 1rem;
    }
    .leaderboard-table td {
        padding: 0.5rem 0.8rem; border-bottom: 1px solid #e0e0d8; color: #1a1a1a;
    }
    .leaderboard-table tr:hover { background-color: #f0f0e8; }
    .leader-row { background-color: #FFF8DC; font-weight: 600; }

    .detail-card {
        background-color: #FFFEF7; border-radius: 8px;
        padding: 1rem 1.2rem; margin-bottom: 0.8rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2); color: #1a1a1a;
    }
    .detail-card h4 {
        color: #006747; font-family: 'EB Garamond', Georgia, serif;
        margin: 0 0 0.6rem 0; font-size: 1.15rem;
    }
    .detail-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .detail-table th {
        background-color: #006747; color: #FFD700;
        padding: 0.4rem 0.6rem; text-align: left; font-size: 0.8rem;
    }
    .detail-table td {
        padding: 0.4rem 0.6rem; border-bottom: 1px solid #e8e8e0; color: #1a1a1a;
    }

    .winner-banner {
        background: linear-gradient(135deg, #006747 0%, #004d35 100%);
        border: 2px solid #FFD700; border-radius: 8px;
        padding: 1rem; text-align: center; margin-bottom: 1rem;
    }
    .winner-banner span {
        color: #FFD700; font-family: 'EB Garamond', Georgia, serif; font-size: 1.2rem;
    }

    @media (max-width: 768px) {
        .leaderboard-table { font-size: 0.82rem; }
        .leaderboard-table th, .leaderboard-table td { padding: 0.4rem; }
    }
</style>
"""


def format_score(score):
    if score == 0:
        return "E"
    return f"{score:+d}"


def score_html(score):
    text = format_score(score)
    if score < 0:
        return f'<span class="score-under">{text}</span>'
    elif score > 0:
        return f'<span class="score-over">{text}</span>'
    return f'<span class="score-even">{text}</span>'


def rank_html(rank):
    if rank == 1:
        cls = "rank-1"
    elif rank == 2:
        cls = "rank-2"
    elif rank == 3:
        cls = "rank-3"
    else:
        cls = "rank-other"
    return f'<span class="rank-badge {cls}">{rank}</span>'


# ---------- Header ----------
st.markdown("""
<div style="text-align: center; padding: 1.5rem 0 0.5rem;">
    <h1 style="font-family: 'EB Garamond', Georgia, serif; color: #FFD700;
               font-size: 2.4rem; letter-spacing: 2px;">
        POOL ARCHIVES
    </h1>
    <p style="color: #c0c0b0; font-family: 'EB Garamond', Georgia, serif;
              font-style: italic;">Past tournament results</p>
</div>
""", unsafe_allow_html=True)

# ---------- Load Archives ----------
archived = get_archived_tournaments()

if not archived:
    st.info("No archived results yet. Results are saved when a tournament is finalized.")
    st.stop()

# Tournament selector
selected_idx = st.selectbox(
    "Select tournament",
    range(len(archived)),
    format_func=lambda i: f"{archived[i]['name']} — {archived[i]['start_date'].strftime('%B %d, %Y')}",
)
tournament = archived[selected_idx]
results = get_results(tournament["id"])

if not results:
    st.warning("No results found for this tournament.")
    st.stop()

# ---------- Winner Banner ----------
winner = results[0]
st.html(f"""
{SHARED_STYLES}
<div class="winner-banner">
    <span>&#127942; {winner['participant_name']} wins the {tournament['name']} pool
    at {format_score(winner['total'])} &#127942;</span>
</div>
""")

# ---------- Final Standings ----------
rows_html = ""
for r in results:
    row_class = ' class="leader-row"' if r["rank"] == 1 else ""
    tb_text = format_score(r["tiebreaker"]) if r["tiebreaker"] is not None else "&mdash;"

    rows_html += f"""
    <tr{row_class}>
        <td>{rank_html(r['rank'])}</td>
        <td>{r['participant_name']}</td>
        <td>{score_html(r['total'])}</td>
        <td>{tb_text}</td>
    </tr>"""

st.html(f"""
{SHARED_STYLES}
<div class="scoreboard">
    <h3>{tournament['name']} — Final Standings</h3>
    <table class="leaderboard-table">
        <thead>
            <tr>
                <th>Pos</th>
                <th>Name</th>
                <th>Total</th>
                <th>Tiebreaker</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
</div>
""")

# ---------- Player Breakdowns ----------
st.markdown("<br>", unsafe_allow_html=True)

selected_participant = st.selectbox(
    "View player breakdown",
    ["All"] + [r["participant_name"] for r in results],
)

show_results = results if selected_participant == "All" else [
    r for r in results if r["participant_name"] == selected_participant
]

for r in show_results:
    players = r["player_details"]

    player_rows_html = ""
    for p in players:
        mc = p.get("missed_cut_penalty", 0)
        wd = p.get("wd_penalty", 0)

        if wd > 0:
            penalty_str = f'<span class="score-mc">+{wd} WD</span>'
        elif mc > 0:
            penalty_str = f'<span class="score-mc">+{mc} MC</span>'
        else:
            penalty_str = "&mdash;"

        bonus = p.get("placement_bonus", 0)
        bonus_str = str(bonus) if bonus != 0 else "&mdash;"

        player_rows_html += f"""
        <tr>
            <td>{p['name']}</td>
            <td>{score_html(p['score'])}</td>
            <td>{penalty_str}</td>
            <td>{bonus_str}</td>
            <td>{score_html(p['total'])}</td>
        </tr>"""

    total_scores = sum(p["score"] for p in players)
    total_penalties = sum(p.get("missed_cut_penalty", 0) + p.get("wd_penalty", 0) for p in players)
    total_bonuses = sum(p.get("placement_bonus", 0) for p in players)

    st.html(f"""
    {SHARED_STYLES}
    <div class="detail-card">
        <h4>{rank_html(r['rank'])} &nbsp; {r['participant_name']} &mdash; {score_html(r['total'])}</h4>
        <table class="detail-table">
            <thead>
                <tr><th>Player</th><th>Score</th><th>Penalty</th><th>Bonus</th><th>Total</th></tr>
            </thead>
            <tbody>{player_rows_html}</tbody>
        </table>
        <div style="margin-top: 0.6rem; font-size: 0.85rem; color: #444;">
            Score: {score_html(total_scores)} &middot;
            Penalties: +{total_penalties} &middot;
            Bonuses: {total_bonuses} &middot;
            <strong>Net: {score_html(r['total'])}</strong>
        </div>
    </div>
    """)
