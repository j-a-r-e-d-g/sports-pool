# db.py
# Database layer for the sports pool platform.
# Uses PostgreSQL (Neon) for persistent storage of tournaments, tiers,
# players, picks, and entries.
#
# Connection string is read from Streamlit secrets (cloud) or .env (local).
# Schema is auto-created on first connection if tables don't exist.

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


def _get_database_url():
    """
    Get the Postgres connection string.
    Checks Streamlit secrets first (cloud), then falls back to environment
    variable DATABASE_URL (local development via .env).
    """
    try:
        import streamlit as st
        if "database" in st.secrets and "url" in st.secrets["database"]:
            return st.secrets["database"]["url"]
    except Exception:
        pass

    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    raise RuntimeError(
        "No database URL found. Set DATABASE_URL in .env or add "
        "[database] url = '...' to .streamlit/secrets.toml"
    )


@contextmanager
def get_conn():
    """
    Context manager that yields a database connection.
    Auto-commits on success, rolls back on error, always closes.
    """
    conn = psycopg2.connect(_get_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Create all tables if they don't exist.
    Safe to call on every app start — uses IF NOT EXISTS.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tournaments (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    espn_event_name TEXT,
                    start_date TIMESTAMP NOT NULL,
                    status TEXT NOT NULL DEFAULT 'setup',
                    theme JSONB,
                    rules JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS tiers (
                    id SERIAL PRIMARY KEY,
                    tournament_id INT NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                    tier_number INT NOT NULL,
                    label TEXT NOT NULL,
                    rank_min INT NOT NULL,
                    rank_max INT,
                    picks_required INT NOT NULL DEFAULT 2
                );

                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY,
                    tournament_id INT NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                    tier_id INT NOT NULL REFERENCES tiers(id) ON DELETE CASCADE,
                    name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS entries (
                    id SERIAL PRIMARY KEY,
                    tournament_id INT NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                    participant_name TEXT NOT NULL,
                    tiebreaker INT,
                    submitted_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(tournament_id, participant_name)
                );

                CREATE TABLE IF NOT EXISTS picks (
                    id SERIAL PRIMARY KEY,
                    entry_id INT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                    tier_id INT NOT NULL REFERENCES tiers(id) ON DELETE CASCADE,
                    player_name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS results (
                    id SERIAL PRIMARY KEY,
                    tournament_id INT NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                    participant_name TEXT NOT NULL,
                    rank INT NOT NULL,
                    total INT NOT NULL,
                    tiebreaker INT,
                    tiebreaker_diff FLOAT,
                    player_details JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );

                -- Add columns if they don't exist (migration for existing DBs)
                DO $$ BEGIN
                    ALTER TABLE tournaments ADD COLUMN theme JSONB;
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
                DO $$ BEGIN
                    ALTER TABLE tournaments ADD COLUMN rules JSONB;
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
            """)


# ---------- Tournament CRUD ----------

def create_tournament(name, espn_event_name, start_date):
    """Create a new tournament. Returns the new tournament ID."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tournaments (name, espn_event_name, start_date) "
                "VALUES (%s, %s, %s) RETURNING id",
                (name, espn_event_name, start_date),
            )
            return cur.fetchone()[0]


def get_tournament(tournament_id):
    """Fetch a single tournament by ID."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tournaments WHERE id = %s", (tournament_id,))
            return cur.fetchone()


def list_tournaments():
    """List all tournaments, newest first."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tournaments ORDER BY start_date DESC")
            return cur.fetchall()


def update_tournament_status(tournament_id, status):
    """Update a tournament's status (setup/open/locked/final)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tournaments SET status = %s WHERE id = %s",
                (status, tournament_id),
            )


def update_tournament_theme(tournament_id, theme_dict):
    """Update a tournament's theme (JSONB)."""
    import json
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tournaments SET theme = %s WHERE id = %s",
                (json.dumps(theme_dict), tournament_id),
            )


def update_tournament_rules(tournament_id, rules_dict):
    """Update a tournament's rules config (JSONB)."""
    import json
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tournaments SET rules = %s WHERE id = %s",
                (json.dumps(rules_dict), tournament_id),
            )


# ---------- Tier CRUD ----------

def create_tier(tournament_id, tier_number, label, rank_min, rank_max, picks_required):
    """Add a tier to a tournament. Returns the tier ID."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tiers (tournament_id, tier_number, label, rank_min, rank_max, picks_required) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (tournament_id, tier_number, label, rank_min, rank_max, picks_required),
            )
            return cur.fetchone()[0]


def get_tiers(tournament_id):
    """Get all tiers for a tournament, ordered by tier number."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM tiers WHERE tournament_id = %s ORDER BY tier_number",
                (tournament_id,),
            )
            return cur.fetchall()


def delete_tiers(tournament_id):
    """Delete all tiers (and their players via CASCADE) for a tournament."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tiers WHERE tournament_id = %s", (tournament_id,))


# ---------- Player CRUD ----------

def add_players(tournament_id, tier_id, player_names):
    """Add multiple players to a tier. Expects a list of name strings."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            for name in player_names:
                cur.execute(
                    "INSERT INTO players (tournament_id, tier_id, name) VALUES (%s, %s, %s)",
                    (tournament_id, tier_id, name),
                )


def get_players_by_tier(tournament_id):
    """
    Get all players grouped by tier for a tournament.
    Returns a dict: {tier_id: [player_name, ...]}
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT p.name, p.tier_id FROM players p "
                "JOIN tiers t ON p.tier_id = t.id "
                "WHERE p.tournament_id = %s ORDER BY t.tier_number, p.name",
                (tournament_id,),
            )
            rows = cur.fetchall()

    grouped = {}
    for row in rows:
        grouped.setdefault(row["tier_id"], []).append(row["name"])
    return grouped


# ---------- Entry / Pick CRUD ----------

def submit_entry(tournament_id, participant_name, tiebreaker, picks_by_tier):
    """
    Submit (or update) a pool entry.

    Args:
        tournament_id: which tournament
        participant_name: who's entering
        tiebreaker: predicted winning score (int)
        picks_by_tier: dict of {tier_id: [player_name, ...]}

    Uses upsert — if the participant already submitted, their entry
    and picks are replaced.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Upsert the entry
            cur.execute(
                "INSERT INTO entries (tournament_id, participant_name, tiebreaker, submitted_at) "
                "VALUES (%s, %s, %s, NOW()) "
                "ON CONFLICT (tournament_id, participant_name) "
                "DO UPDATE SET tiebreaker = EXCLUDED.tiebreaker, submitted_at = NOW() "
                "RETURNING id",
                (tournament_id, participant_name, tiebreaker),
            )
            entry_id = cur.fetchone()[0]

            # Clear old picks and insert new ones
            cur.execute("DELETE FROM picks WHERE entry_id = %s", (entry_id,))
            for tier_id, player_names in picks_by_tier.items():
                for name in player_names:
                    cur.execute(
                        "INSERT INTO picks (entry_id, tier_id, player_name) "
                        "VALUES (%s, %s, %s)",
                        (entry_id, tier_id, name),
                    )

            return entry_id


def get_entries(tournament_id):
    """
    Get all entries for a tournament in the format the scoring engine expects.

    Returns a list of dicts:
        [{"name": "Jared", "picks": ["Player1", ...], "tiebreaker": -12}, ...]
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all entries
            cur.execute(
                "SELECT id, participant_name, tiebreaker FROM entries "
                "WHERE tournament_id = %s ORDER BY submitted_at",
                (tournament_id,),
            )
            entries = cur.fetchall()

            results = []
            for entry in entries:
                # Get picks ordered by tier
                cur.execute(
                    "SELECT p.player_name FROM picks p "
                    "JOIN tiers t ON p.tier_id = t.id "
                    "WHERE p.entry_id = %s ORDER BY t.tier_number, p.player_name",
                    (entry["id"],),
                )
                pick_rows = cur.fetchall()

                results.append({
                    "name": entry["participant_name"],
                    "picks": [r["player_name"] for r in pick_rows],
                    "tiebreaker": entry["tiebreaker"],
                })

            return results


def get_entry_count(tournament_id):
    """Get the number of entries for a tournament."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM entries WHERE tournament_id = %s",
                (tournament_id,),
            )
            return cur.fetchone()[0]


def has_entered(tournament_id, participant_name):
    """Check if a participant has already entered a tournament."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM entries WHERE tournament_id = %s AND participant_name = %s",
                (tournament_id, participant_name),
            )
            return cur.fetchone()[0] > 0


# ---------- Results (Archives) ----------

def save_results(tournament_id, leaderboard):
    """
    Snapshot final leaderboard results for a tournament.
    Stores each participant's rank, total, tiebreaker, and full
    per-player breakdown as JSONB so archives don't need ESPN data.

    leaderboard: list of dicts from calculate_leaderboard()
    """
    import json
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clear any existing results for this tournament
            cur.execute("DELETE FROM results WHERE tournament_id = %s", (tournament_id,))
            for entry in leaderboard:
                cur.execute(
                    "INSERT INTO results "
                    "(tournament_id, participant_name, rank, total, tiebreaker, tiebreaker_diff, player_details) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        tournament_id,
                        entry["name"],
                        entry["rank"],
                        entry["total"],
                        entry.get("tiebreaker"),
                        entry.get("tiebreaker_diff"),
                        json.dumps(entry["players"]),
                    ),
                )


def get_results(tournament_id):
    """
    Get archived results for a tournament, sorted by rank.
    Returns a list of dicts with rank, name, total, tiebreaker, player_details.
    """
    import json
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM results WHERE tournament_id = %s ORDER BY rank",
                (tournament_id,),
            )
            rows = cur.fetchall()
            for row in rows:
                if isinstance(row["player_details"], str):
                    row["player_details"] = json.loads(row["player_details"])
            return rows


def get_archived_tournaments():
    """Get all tournaments that have archived results."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT DISTINCT t.* FROM tournaments t "
                "JOIN results r ON t.id = r.tournament_id "
                "ORDER BY t.start_date DESC"
            )
            return cur.fetchall()


def get_all_results():
    """
    Get all results across all tournaments.
    Returns list of dicts with tournament_name, participant_name, rank, total.
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT r.participant_name, r.rank, r.total, "
                "t.name AS tournament_name, t.start_date "
                "FROM results r "
                "JOIN tournaments t ON r.tournament_id = t.id "
                "ORDER BY t.start_date, r.rank"
            )
            return cur.fetchall()
