# Submit Picks page — in-app pick submission form for pool participants.
# Participants pick players from each tier, enter their tiebreaker
# prediction, and submit directly to Postgres.

import sys
import os

# Add pga/ to path so we can import db, scoring, etc.
_pga_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _pga_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_pga_dir, "..", ".env"))

import streamlit as st
from db import (
    init_db, list_tournaments, get_tournament, get_tiers,
    get_players_by_tier, submit_entry, has_entered, get_entry_count,
)
from themes import get_theme, theme_css, header_html

st.set_page_config(page_title="Submit Picks", page_icon="⛳", layout="centered")

init_db()

# ---------- Tournament Selection ----------
tournaments = list_tournaments()
open_tournaments = [t for t in tournaments if t["status"] == "open"]

if not open_tournaments:
    # Apply default theme before stopping
    from themes import DEFAULT_THEME
    st.markdown(theme_css(DEFAULT_THEME), unsafe_allow_html=True)
    st.warning("No tournaments are currently accepting picks. Check back soon!")
    st.stop()

if len(open_tournaments) == 1:
    tournament = open_tournaments[0]
else:
    # Apply default theme for selector
    from themes import DEFAULT_THEME
    st.markdown(theme_css(DEFAULT_THEME), unsafe_allow_html=True)
    selected = st.selectbox(
        "Select tournament",
        range(len(open_tournaments)),
        format_func=lambda i: open_tournaments[i]["name"],
    )
    tournament = open_tournaments[selected]

tid = tournament["id"]
tiers = get_tiers(tid)
players_by_tier = get_players_by_tier(tid)

# Apply tournament theme
_theme = get_theme(tournament)
st.markdown(theme_css(_theme), unsafe_allow_html=True)
st.html(header_html(_theme, "SUBMIT YOUR PICKS"))

if not tiers:
    st.error("This tournament hasn't been set up yet. Check back soon!")
    st.stop()

st.markdown("""
<div style="text-align: center; color: #E6E6E6; font-family: 'Inter', sans-serif;
            font-size: 1.1rem; margin-bottom: 1rem;">
    %s &middot; %s
    <br><span style="font-size: 0.9rem; color: #8B8D93;">
        %s entries so far
    </span>
</div>
""" % (tournament["name"], tournament["start_date"].strftime("%B %d, %Y"), get_entry_count(tid)),
unsafe_allow_html=True)

# ---------- Rules Summary ----------
from themes import shared_styles
rules = tournament.get("rules") or {}
if rules:
    STYLES = shared_styles(_theme)
    buy_in = rules.get("buy_in", 10)
    p1 = rules.get("payout_1st", 100)
    p2 = rules.get("payout_2nd", 50)
    p3 = rules.get("payout_3rd", 20)
    mc_r3 = rules.get("mc_r3", 5)
    mc_r4 = rules.get("mc_r4", 6)
    mc_total = mc_r3 + mc_r4
    wd_pen = rules.get("wd_penalty", 15)
    bonuses = rules.get("bonuses", {})
    top10 = rules.get("top10_bonus", 10)
    notes = rules.get("notes", "")

    # Build tier rows
    tier_rows = ""
    for t in tiers:
        rmax = t["rank_max"] if t["rank_max"] else "+"
        tier_rows += "<tr><td>%s</td><td>%s &ndash; %s</td><td>%s</td></tr>" % (
            t["label"], t["rank_min"], rmax, t["picks_required"])

    # Build bonus rows
    bonus_rows = ""
    for pos, label in [("1st", "1st"), ("2nd", "2nd"), ("3rd", "3rd"), ("4th", "4th"), ("5th", "5th")]:
        val = bonuses.get(pos, 0)
        if val > 0:
            bonus_rows += "<tr><td>%s</td><td>-%d</td></tr>" % (label, val)
    if top10 > 0:
        bonus_rows += "<tr><td>6th &ndash; 10th</td><td>-%d</td></tr>" % top10

    notes_html = ""
    if notes:
        notes_html = "<h4>Special Rules</h4><p>%s</p>" % notes

    st.html("""%s
    <div class="detail-card" style="margin-bottom: 1rem;">
        <h4>Rules &amp; Payouts</h4>
        <p style="color: #8B8D93; font-size: 0.85rem; margin-bottom: 0.8rem;">
            <strong style="color: #E6E6E6;">$%d buy-in</strong> &middot;
            1st: $%d &middot; 2nd: $%d &middot; 3rd: $%d
        </p>

        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 200px;">
                <h4 style="font-size: 0.85rem;">Tiers</h4>
                <table class="detail-table">
                    <tr><th>Tier</th><th>Ranks</th><th>Picks</th></tr>
                    %s
                </table>
            </div>
            <div style="flex: 1; min-width: 150px;">
                <h4 style="font-size: 0.85rem;">Placement Bonuses</h4>
                <table class="detail-table">
                    <tr><th>Finish</th><th>Bonus</th></tr>
                    %s
                </table>
            </div>
            <div style="flex: 1; min-width: 150px;">
                <h4 style="font-size: 0.85rem;">Penalties</h4>
                <table class="detail-table">
                    <tr><th>Type</th><th>Strokes</th></tr>
                    <tr><td>Missed Cut (R3)</td><td>+%d</td></tr>
                    <tr><td>Missed Cut (R4)</td><td>+%d</td></tr>
                    <tr><td><strong>MC Total</strong></td><td><strong>+%d</strong></td></tr>
                    <tr><td>Withdrawal</td><td>+%d</td></tr>
                </table>
            </div>
        </div>
        %s
        <p style="color: #8B8D93; font-size: 0.8rem; margin-top: 0.8rem;">
            Lowest cumulative score wins. Tiebreaker: closest prediction to the winning score.
        </p>
    </div>
    """ % (STYLES, buy_in, p1, p2, p3, tier_rows, bonus_rows,
           mc_r3, mc_r4, mc_total, wd_pen, notes_html))

# ---------- Pick Form ----------
with st.form("pick_form"):
    name = st.text_input("Your name", placeholder="Enter your name")

    st.divider()

    # Dynamic tier selections
    picks_by_tier = {}

    for tier in tiers:
        tier_players = players_by_tier.get(tier["id"], [])
        rank_max = tier["rank_max"] if tier["rank_max"] else "+"
        picks_required = tier["picks_required"]

        st.markdown(f"**{tier['label']}** — Ranks {tier['rank_min']}-{rank_max} "
                     f"*(pick {picks_required})*")

        if not tier_players:
            st.warning(f"No players loaded for {tier['label']} yet")
            picks_by_tier[tier["id"]] = []
            continue

        selected_players = []
        cols = st.columns(picks_required)
        for j in range(picks_required):
            with cols[j]:
                pick = st.selectbox(
                    f"Pick {j + 1}",
                    ["-- Select --"] + tier_players,
                    key=f"pick_{tier['id']}_{j}",
                    label_visibility="collapsed" if j > 0 else "visible",
                )
                if pick != "-- Select --":
                    selected_players.append(pick)

        picks_by_tier[tier["id"]] = selected_players

    st.divider()

    tiebreaker = st.number_input(
        "Tiebreaker: Predict the winning score (relative to par, e.g. -12)",
        min_value=-30,
        max_value=20,
        value=-10,
        step=1,
    )

    submitted = st.form_submit_button("Submit Picks", type="primary", use_container_width=True)

if submitted:
    errors = []

    if not name or not name.strip():
        errors.append("Please enter your name")

    for tier in tiers:
        selected = picks_by_tier.get(tier["id"], [])
        if len(selected) != tier["picks_required"]:
            errors.append(f"{tier['label']}: select {tier['picks_required']} player(s) "
                         f"(you picked {len(selected)})")

    for tier in tiers:
        selected = picks_by_tier.get(tier["id"], [])
        if len(selected) != len(set(selected)):
            errors.append(f"{tier['label']}: can't pick the same player twice")

    if errors:
        for err in errors:
            st.error(err)
    else:
        fresh = get_tournament(tid)
        if fresh["status"] != "open":
            st.error("This tournament is no longer accepting picks!")
        else:
            already_entered = has_entered(tid, name.strip())
            entry_id = submit_entry(tid, name.strip(), tiebreaker, picks_by_tier)

            if already_entered:
                st.success(f"Updated your picks, {name.strip()}! Entry #{entry_id} saved.")
            else:
                st.success(f"You're in, {name.strip()}! Entry #{entry_id} confirmed.")

            st.balloons()

            st.markdown("---")
            st.markdown("**Your picks:**")
            for tier in tiers:
                selected = picks_by_tier.get(tier["id"], [])
                st.write(f"**{tier['label']}:** {', '.join(selected)}")
            st.write(f"**Tiebreaker:** {tiebreaker:+d}")
