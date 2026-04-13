# Money List page — all-time earnings leaderboard across pool tournaments.

import sys
import os

_pga_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _pga_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_pga_dir, "..", ".env"))

import streamlit as st
from db import init_db, get_all_results
from themes import DEFAULT_THEME, theme_css, shared_styles, header_html

st.set_page_config(page_title="Money List", page_icon="⛳", layout="wide")

init_db()

# ---------- Theme ----------
_theme = DEFAULT_THEME
st.markdown(theme_css(_theme), unsafe_allow_html=True)
SHARED_STYLES = shared_styles(_theme) + """
<style>
    .money-pos { color: #2ECC71; font-weight: 700; }
    .money-neg { color: #E74C3C; font-weight: 600; }

    /* Mobile: hide less important columns, tighten spacing */
    .hide-mobile { }
    @media (max-width: 600px) {
        .hide-mobile { display: none; }
        .leaderboard-table { font-size: 0.78rem; }
        .leaderboard-table th, .leaderboard-table td { padding: 0.35rem 0.4rem; }
        .detail-table { font-size: 0.75rem; }
        .detail-table th, .detail-table td { padding: 0.3rem 0.4rem; }
        .rank-badge { width: 22px; height: 22px; line-height: 22px; font-size: 0.7rem; }
        .scoreboard { padding: 0.8rem; }
        .scoreboard h3 { font-size: 0.95rem; }
    }
</style>
"""

# ---------- Payout structure ----------
# Maps finish position to payout amount
PAYOUTS = {1: 100, 2: 50, 3: 20}
ENTRY_FEE = 10

# ---------- Header ----------
st.html(header_html(_theme, "ALL-TIME MONEY LIST", "Career earnings across pool tournaments"))

# ---------- Load Data ----------
all_results = get_all_results()

if not all_results:
    st.info("No results yet. The money list will populate as tournaments are archived.")
    st.stop()

# Build money list: {name: {earnings, tournaments, wins, top3, results: [...]}}
money = {}
for r in all_results:
    name = r["participant_name"]
    if name not in money:
        money[name] = {
            "earnings": 0,
            "spent": 0,
            "tournaments": 0,
            "wins": 0,
            "top3": 0,
            "results": [],
        }

    payout = PAYOUTS.get(r["rank"], 0)
    money[name]["earnings"] += payout
    money[name]["spent"] += ENTRY_FEE
    money[name]["tournaments"] += 1
    if r["rank"] == 1:
        money[name]["wins"] += 1
    if r["rank"] <= 3:
        money[name]["top3"] += 1
    money[name]["results"].append({
        "tournament": r["tournament_name"],
        "rank": r["rank"],
        "total": r["total"],
        "payout": payout,
    })

# Sort by net earnings (profit), then by wins
standings = sorted(
    money.items(),
    key=lambda x: (-x[1]["earnings"] + x[1]["spent"], -x[1]["wins"]),
)

# ---------- Money List Table ----------
rows_html = ""
for i, (name, data) in enumerate(standings):
    net = data["earnings"] - data["spent"]
    rank = i + 1

    if rank == 1:
        rank_cls = "rank-1"
    elif rank == 2:
        rank_cls = "rank-2"
    elif rank == 3:
        rank_cls = "rank-3"
    else:
        rank_cls = "rank-other"

    # Format earnings
    earnings_str = "$%d" % data["earnings"] if data["earnings"] > 0 else "&mdash;"
    net_str = "+$%d" % net if net > 0 else ("-$%d" % abs(net) if net < 0 else "E")
    net_cls = "money-pos" if net > 0 else ("money-neg" if net < 0 else "score-even")

    wins_str = str(data["wins"]) if data["wins"] > 0 else "&mdash;"
    top3_str = str(data["top3"]) if data["top3"] > 0 else "&mdash;"

    rows_html += """
    <tr%s>
        <td><span class="rank-badge %s">%d</span></td>
        <td>%s</td>
        <td class="hide-mobile">%d</td>
        <td class="hide-mobile">%s</td>
        <td class="hide-mobile">%s</td>
        <td>%s</td>
        <td><span class="%s">%s</span></td>
    </tr>""" % (
        ' class="leader-row"' if rank == 1 else "",
        rank_cls, rank, name,
        data["tournaments"], wins_str, top3_str,
        earnings_str, net_cls, net_str,
    )

st.html("""%s
<div class="scoreboard">
    <h3>All-Time Money List</h3>
    <p style="font-size: 0.85rem; color: #666; margin-bottom: 0.8rem;">
        $%d entry &middot; 1st: $%d &middot; 2nd: $%d &middot; 3rd: $%d
    </p>
    <table class="leaderboard-table">
        <thead>
            <tr>
                <th>Pos</th>
                <th>Name</th>
                <th class="hide-mobile">Events</th>
                <th class="hide-mobile">Wins</th>
                <th class="hide-mobile">Top 3</th>
                <th>Earnings</th>
                <th>Net</th>
            </tr>
        </thead>
        <tbody>%s</tbody>
    </table>
</div>
""" % (SHARED_STYLES, ENTRY_FEE, PAYOUTS[1], PAYOUTS[2], PAYOUTS[3], rows_html))

# ---------- Tournament History ----------
st.markdown("<br>", unsafe_allow_html=True)

selected_player = st.selectbox(
    "View tournament history",
    [name for name, _ in standings],
)

if selected_player:
    player_data = money[selected_player]
    history_rows = ""
    for res in player_data["results"]:
        payout_str = "$%d" % res["payout"] if res["payout"] > 0 else "&mdash;"
        history_rows += """
        <tr>
            <td>%s</td>
            <td>%d</td>
            <td>%s</td>
            <td>%s</td>
        </tr>""" % (
            res["tournament"],
            res["rank"],
            "%+d" % res["total"] if res["total"] != 0 else "E",
            payout_str,
        )

    total_earned = player_data["earnings"]
    total_spent = player_data["spent"]
    net = total_earned - total_spent

    st.html("""%s
    <div class="detail-card">
        <h4>%s &mdash; Tournament History</h4>
        <table class="detail-table">
            <thead>
                <tr><th>Tournament</th><th>Finish</th><th>Score</th><th>Payout</th></tr>
            </thead>
            <tbody>%s</tbody>
        </table>
        <div style="margin-top: 0.6rem; font-size: 0.85rem; color: #444;">
            %d events &middot;
            Earned: $%d &middot;
            Spent: $%d &middot;
            <strong>Net: %s</strong>
        </div>
    </div>
    """ % (
        SHARED_STYLES,
        selected_player,
        history_rows,
        player_data["tournaments"],
        total_earned,
        total_spent,
        "+$%d" % net if net > 0 else ("-$%d" % abs(net) if net < 0 else "Even"),
    ))
