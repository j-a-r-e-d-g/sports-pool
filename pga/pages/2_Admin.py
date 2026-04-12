# Admin page — create tournaments, configure tiers, add players.
# Password protected so only the pool runner can access it.

import sys
import os

_pga_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _pga_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_pga_dir, "..", ".env"))

import streamlit as st
from datetime import datetime, date, time
from db import (
    init_db, create_tournament, list_tournaments, get_tournament,
    update_tournament_status, create_tier, get_tiers, delete_tiers,
    add_players, get_players_by_tier, get_entry_count, get_entries,
    save_results,
)

st.set_page_config(page_title="Pool Admin", page_icon="⛳", layout="wide")

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

# ---------- Password Gate ----------
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
if not ADMIN_PASSWORD:
    try:
        if "admin" in st.secrets and "password" in st.secrets["admin"]:
            ADMIN_PASSWORD = st.secrets["admin"]["password"]
    except Exception:
        pass

if not ADMIN_PASSWORD:
    st.error("Admin password not configured. Set ADMIN_PASSWORD in .env or [admin] password in secrets.")
    st.stop()

if "admin_auth" not in st.session_state:
    st.session_state.admin_auth = False

if not st.session_state.admin_auth:
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-family: 'EB Garamond', Georgia, serif; color: #FFD700;
                   font-size: 2rem; letter-spacing: 2px;">
            POOL ADMIN
        </h1>
    </div>
    """, unsafe_allow_html=True)

    password = st.text_input("Enter admin password", type="password")
    if st.button("Login"):
        if password == ADMIN_PASSWORD:
            st.session_state.admin_auth = True
            st.rerun()
        else:
            st.error("Wrong password")
    st.stop()

# ---------- Admin Interface ----------
st.markdown("""
<div style="text-align: center; padding: 1rem 0;">
    <h1 style="font-family: 'EB Garamond', Georgia, serif; color: #FFD700;
               font-size: 2rem; letter-spacing: 2px;">
        POOL ADMIN
    </h1>
</div>
""", unsafe_allow_html=True)

# ---------- Sidebar: Tournament Selector ----------
tournaments = list_tournaments()
tournament_names = [f"{t['name']} ({t['start_date'].strftime('%b %d')})" for t in tournaments]

st.sidebar.header("Tournaments")

with st.sidebar.expander("Create New Tournament"):
    new_name = st.text_input("Tournament name", placeholder="RBC Heritage 2026")
    new_espn = st.text_input("ESPN event name (for matching)", placeholder="RBC Heritage")
    new_date = st.date_input("Start date", value=date.today())
    new_time = st.time_input("Start time (ET)", value=time(7, 0))
    if st.button("Create Tournament"):
        if new_name:
            start_dt = datetime.combine(new_date, new_time)
            tid = create_tournament(new_name, new_espn, start_dt)
            st.success(f"Created '{new_name}' (ID: {tid})")
            st.rerun()
        else:
            st.error("Enter a tournament name")

if not tournaments:
    st.info("No tournaments yet. Create one in the sidebar.")
    st.stop()

selected_idx = st.sidebar.selectbox(
    "Select tournament",
    range(len(tournaments)),
    format_func=lambda i: tournament_names[i],
)
tournament = tournaments[selected_idx]
tid = tournament["id"]

# ---------- Tournament Status ----------
st.subheader(tournament["name"])

col_status, col_entries, col_actions = st.columns([2, 1, 3])

with col_status:
    status_icons = {"setup": "🔧", "open": "🟢", "locked": "🔒", "live": "📡", "final": "🏁"}
    st.metric("Status", f"{status_icons.get(tournament['status'], '')} {tournament['status'].upper()}")

with col_entries:
    entry_count = get_entry_count(tid)
    st.metric("Entries", entry_count)

with col_actions:
    st.write("**Change status:**")
    status_cols = st.columns(4)
    statuses = ["open", "locked", "live", "final"]
    for i, s in enumerate(statuses):
        with status_cols[i]:
            if st.button(s.upper(), key=f"status_{s}"):
                update_tournament_status(tid, s)
                st.rerun()

# ---------- Archive Results ----------
if tournament["status"] in ("live", "final") and entry_count > 0:
    st.write("**Archive results:**")
    st.caption(
        "Snapshot the current leaderboard to the Archives page. "
        "Requires live ESPN scores. Safe to run multiple times — overwrites previous snapshot."
    )
    if st.button("Archive Results", type="primary"):
        try:
            from live_scores import parse_tournament_scores
            from scoring import calculate_leaderboard

            espn_name = tournament.get("espn_event_name") or tournament["name"]
            scores = parse_tournament_scores(espn_name)
            if not scores:
                st.error("Could not load ESPN scores. Make sure the ESPN event name matches.")
            else:
                entries = get_entries(tid)
                tiers = get_tiers(tid)
                pool_tiers = [
                    {"label": t["label"], "rank_min": t["rank_min"],
                     "rank_max": t["rank_max"], "picks_required": t["picks_required"]}
                    for t in tiers
                ]
                leaderboard = calculate_leaderboard(entries, scores)
                save_results(tid, leaderboard)
                st.success(f"Archived {len(leaderboard)} results for {tournament['name']}!")
                st.balloons()
        except Exception as e:
            st.error(f"Error archiving results: {e}")

st.divider()

# ---------- Tier Configuration ----------
st.subheader("Tier Setup")

existing_tiers = get_tiers(tid)
players_by_tier = get_players_by_tier(tid)

if existing_tiers:
    st.write("**Current tiers:**")
    for tier in existing_tiers:
        rank_max = tier["rank_max"] if tier["rank_max"] else "+"
        player_list = players_by_tier.get(tier["id"], [])
        st.write(
            f"**{tier['label']}** — Ranks {tier['rank_min']}-{rank_max}, "
            f"{tier['picks_required']} picks, {len(player_list)} players loaded"
        )

    if st.button("Clear all tiers and re-configure", type="secondary"):
        delete_tiers(tid)
        st.rerun()

    st.divider()

with st.expander("Configure Tiers" if not existing_tiers else "Add More Tiers"):
    st.write("Define your tier structure. Each tier has a rank range and number of picks required.")

    num_tiers = st.number_input("Number of tiers", min_value=1, max_value=10, value=5)

    tier_configs = []
    for i in range(num_tiers):
        st.write(f"**Tier {i + 1}**")
        cols = st.columns(4)
        with cols[0]:
            label = st.text_input("Label", value=f"Tier {i + 1}", key=f"tier_label_{i}")
        with cols[1]:
            rank_min = st.number_input("Rank min", value=1 if i == 0 else 0, min_value=1, key=f"tier_min_{i}")
        with cols[2]:
            rank_max = st.number_input("Rank max (0 = no limit)", value=0, min_value=0, key=f"tier_max_{i}")
        with cols[3]:
            picks_req = st.number_input("Picks required", value=2, min_value=1, max_value=10, key=f"tier_picks_{i}")

        tier_configs.append({
            "tier_number": i + 1,
            "label": label,
            "rank_min": rank_min,
            "rank_max": rank_max if rank_max > 0 else None,
            "picks_required": picks_req,
        })

    if st.button("Save Tiers"):
        for tc in tier_configs:
            create_tier(tid, tc["tier_number"], tc["label"], tc["rank_min"], tc["rank_max"], tc["picks_required"])
        st.success(f"Created {len(tier_configs)} tiers")
        st.rerun()

# ---------- Player Assignment ----------
if existing_tiers:
    st.divider()
    st.subheader("Players")

    st.write(
        "Paste player names for each tier (one per line). "
        "You can pull these from odds/rankings or enter manually."
    )

    for tier in existing_tiers:
        current_players = players_by_tier.get(tier["id"], [])
        with st.expander(f"{tier['label']} ({len(current_players)} players)"):
            if current_players:
                st.write(", ".join(current_players))

            player_text = st.text_area(
                f"Add players to {tier['label']} (one per line)",
                key=f"players_{tier['id']}",
                height=150,
            )

            if st.button(f"Add to {tier['label']}", key=f"add_players_{tier['id']}"):
                names = [n.strip() for n in player_text.strip().split("\n") if n.strip()]
                if names:
                    add_players(tid, tier["id"], names)
                    st.success(f"Added {len(names)} players to {tier['label']}")
                    st.rerun()
                else:
                    st.warning("No player names entered")

# ---------- Entries ----------
if entry_count > 0:
    st.divider()
    st.subheader(f"Entries ({entry_count})")

    entries = get_entries(tid)
    for entry in entries:
        with st.expander(f"{entry['name']} (TB: {entry['tiebreaker']})"):
            for i, pick in enumerate(entry["picks"]):
                tier_num = (i // existing_tiers[0]["picks_required"]) + 1 if existing_tiers else "?"
                st.write(f"Tier {tier_num}: {pick}")
