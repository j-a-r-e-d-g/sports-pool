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

st.set_page_config(page_title="Submit Picks", page_icon="⛳", layout="centered")

init_db()

# ---------- Theme ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600;700&display=swap');
    .stApp { background-color: #006747; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; padding: 1rem 0;">
    <h1 style="font-family: 'EB Garamond', Georgia, serif; color: #FFD700;
               font-size: 2.2rem; margin: 0; letter-spacing: 2px;">
        SUBMIT YOUR PICKS
    </h1>
</div>
""", unsafe_allow_html=True)

# ---------- Tournament Selection ----------
tournaments = list_tournaments()
open_tournaments = [t for t in tournaments if t["status"] == "open"]

if not open_tournaments:
    st.warning("No tournaments are currently accepting picks. Check back soon!")
    st.stop()

if len(open_tournaments) == 1:
    tournament = open_tournaments[0]
else:
    selected = st.selectbox(
        "Select tournament",
        range(len(open_tournaments)),
        format_func=lambda i: open_tournaments[i]["name"],
    )
    tournament = open_tournaments[selected]

tid = tournament["id"]
tiers = get_tiers(tid)
players_by_tier = get_players_by_tier(tid)

if not tiers:
    st.error("This tournament hasn't been set up yet. Check back soon!")
    st.stop()

st.markdown(f"""
<div style="text-align: center; color: #f5f5f0; font-family: 'EB Garamond', Georgia, serif;
            font-size: 1.1rem; margin-bottom: 1rem;">
    {tournament['name']} &middot; {tournament['start_date'].strftime('%B %d, %Y')}
    <br><span style="font-size: 0.9rem; color: #c0c0b0;">
        {get_entry_count(tid)} entries so far
    </span>
</div>
""", unsafe_allow_html=True)

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
