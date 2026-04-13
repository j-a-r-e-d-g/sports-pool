# themes.py
# Dynamic per-tournament theming for the sports pool platform.
# Each tournament can have its own color scheme stored in the DB.
# Presets are provided for well-known PGA Tour events.

PRESETS = {
    "masters": {
        "name": "The Masters",
        "bg": "#006747",
        "bg_dark": "#004d35",
        "primary": "#FFD700",
        "accent": "#CE1141",
    },
    "rbc_heritage": {
        "name": "RBC Heritage",
        "bg": "#1B2A4A",
        "bg_dark": "#0F1D33",
        "primary": "#E31837",
        "accent": "#F4D03F",
    },
    "pga_championship": {
        "name": "PGA Championship",
        "bg": "#00205B",
        "bg_dark": "#001440",
        "primary": "#CFB53B",
        "accent": "#FFFFFF",
    },
    "us_open": {
        "name": "US Open",
        "bg": "#003366",
        "bg_dark": "#002244",
        "primary": "#CC0000",
        "accent": "#FFFFFF",
    },
    "the_open": {
        "name": "The Open",
        "bg": "#1C2841",
        "bg_dark": "#0E1A2B",
        "primary": "#C8A951",
        "accent": "#FFFFFF",
    },
    "the_players": {
        "name": "THE PLAYERS",
        "bg": "#003057",
        "bg_dark": "#001F3D",
        "primary": "#E8D44D",
        "accent": "#DC4405",
    },
    "memorial": {
        "name": "the Memorial Tournament",
        "bg": "#1A3C34",
        "bg_dark": "#0E2620",
        "primary": "#C9B037",
        "accent": "#FFFFFF",
    },
    "default": {
        "name": "Default",
        "bg": "#2C3E50",
        "bg_dark": "#1A252F",
        "primary": "#3498DB",
        "accent": "#E74C3C",
    },
}

# Default theme used when no tournament-specific theme is set
DEFAULT_THEME = PRESETS["default"]


def get_theme(tournament=None):
    """
    Get the theme for a tournament.
    Checks tournament['theme'] JSONB first, then falls back to default.
    """
    if tournament and tournament.get("theme"):
        theme = tournament["theme"]
        # Ensure all keys exist
        for key in ("bg", "bg_dark", "primary", "accent"):
            if key not in theme:
                theme[key] = DEFAULT_THEME[key]
        return theme
    return DEFAULT_THEME


def theme_css(theme):
    """
    Generate the full CSS for a theme. Used by all pages.
    Returns an HTML <style> block ready for st.markdown(unsafe_allow_html=True).
    """
    bg = theme["bg"]
    bg_dark = theme["bg_dark"]
    primary = theme["primary"]
    accent = theme["accent"]

    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600;700&display=swap');
    .stApp { background-color: %(bg)s; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: %(bg_dark)s; border-radius: 8px; padding: 0.3rem; }
    .stTabs [data-baseweb="tab"] { color: #c0c0b0; font-family: 'EB Garamond', Georgia, serif; font-size: 1.05rem; }
    .stTabs [aria-selected="true"] { color: %(primary)s !important; border-bottom-color: %(primary)s !important; }

    /* Selectbox labels */
    .stSelectbox label { color: #f5f5f0 !important; }
</style>
""" % {"bg": bg, "bg_dark": bg_dark, "primary": primary, "accent": accent}


def shared_styles(theme):
    """
    Generate shared component styles (scoreboards, cards, tables, badges).
    Used inside st.html() blocks.
    """
    bg = theme["bg"]
    bg_dark = theme["bg_dark"]
    primary = theme["primary"]
    accent = theme["accent"]

    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;600;700&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

    .score-under { color: %(accent)s; font-weight: 700; }
    .score-over { color: #1a1a1a; font-weight: 600; }
    .score-even { color: #1a1a1a; font-weight: 600; }
    .score-mc { color: #8B4513; font-style: italic; }
    .score-wd { color: #8B0000; font-style: italic; }

    .bonus-badge {
        display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px;
        font-weight: 700; font-size: 0.8rem;
        background-color: %(bg)s; color: %(primary)s;
    }
    .bonus-none { color: #999; }

    .picked-tag {
        display: inline-block; padding: 0.1rem 0.4rem; border-radius: 4px;
        font-size: 0.75rem; margin: 1px;
        background-color: #e8f5e9; color: #2e7d32;
    }
    .tier-tag {
        display: inline-block; padding: 0.05rem 0.3rem; border-radius: 3px;
        font-size: 0.65rem; margin-left: 2px;
        background-color: #fff3e0; color: #e65100;
    }

    .rank-badge {
        display: inline-block;
        width: 28px; height: 28px; line-height: 28px;
        text-align: center; border-radius: 50%%;
        font-weight: 700; font-size: 0.85rem;
    }
    .rank-1 { background-color: #FFD700; color: %(bg)s; }
    .rank-2 { background-color: #C0C0C0; color: #333; }
    .rank-3 { background-color: #CD7F32; color: #fff; }
    .rank-other { background-color: #e8e8e0; color: #333; }

    .scoreboard {
        background-color: #FFFEF7; border-radius: 8px;
        padding: 1.2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3); color: #1a1a1a;
    }
    .scoreboard h3 {
        color: %(bg)s; font-family: 'EB Garamond', Georgia, serif;
        font-size: 1.3rem; border-bottom: 2px solid %(bg)s;
        padding-bottom: 0.4rem; margin-bottom: 0.8rem;
    }
    .leaderboard-table { width: 100%%; border-collapse: collapse; font-size: 0.95rem; }
    .leaderboard-table th {
        background-color: %(bg)s; color: %(primary)s;
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
        color: %(bg)s; font-family: 'EB Garamond', Georgia, serif;
        margin: 0 0 0.6rem 0; font-size: 1.15rem;
    }
    .detail-table { width: 100%%; border-collapse: collapse; font-size: 0.85rem; }
    .detail-table th {
        background-color: %(bg)s; color: %(primary)s;
        padding: 0.4rem 0.6rem; text-align: left; font-size: 0.8rem;
    }
    .detail-table td {
        padding: 0.4rem 0.6rem; border-bottom: 1px solid #e8e8e0; color: #1a1a1a;
    }

    .rules-card {
        background-color: #FFFEF7; border-radius: 8px;
        padding: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.3); color: #1a1a1a;
    }
    .rules-card h3 {
        color: %(bg)s; font-family: 'EB Garamond', Georgia, serif;
        font-size: 1.2rem; border-bottom: 2px solid %(bg)s;
        padding-bottom: 0.4rem; margin-bottom: 0.8rem;
    }
    .rules-card table {
        width: 100%%; border-collapse: collapse; margin: 0.8rem 0 1.2rem;
    }
    .rules-card th {
        background-color: %(bg)s; color: %(primary)s;
        padding: 0.5rem 0.8rem; text-align: left;
    }
    .rules-card td {
        padding: 0.5rem 0.8rem; border-bottom: 1px solid #e0e0d8;
    }

    .winner-banner {
        background: linear-gradient(135deg, %(bg)s 0%%, %(bg_dark)s 100%%);
        border: 2px solid %(primary)s; border-radius: 8px;
        padding: 1rem; text-align: center; margin-bottom: 1rem;
    }
    .winner-banner span {
        color: %(primary)s; font-family: 'EB Garamond', Georgia, serif; font-size: 1.2rem;
    }

    @media (max-width: 768px) {
        .leaderboard-table { font-size: 0.82rem; }
        .leaderboard-table th, .leaderboard-table td { padding: 0.4rem; }
    }
</style>
""" % {"bg": bg, "bg_dark": bg_dark, "primary": primary, "accent": accent}


def header_html(theme, title, subtitle=""):
    """Generate the page header HTML."""
    primary = theme["primary"]
    html = """
<div style="text-align: center; padding: 1.5rem 0 0.5rem;">
    <h1 style="font-family: 'EB Garamond', Georgia, serif; color: %(primary)s;
               font-size: 2.4rem; letter-spacing: 2px;
               text-shadow: 1px 1px 3px rgba(0,0,0,0.3);">
        %(title)s
    </h1>
""" % {"primary": primary, "title": title}

    if subtitle:
        html += """
    <p style="color: #f5f5f0; font-family: 'EB Garamond', Georgia, serif;
              font-style: italic;">%s</p>
""" % subtitle

    html += "</div>"

    # Accent divider
    html += """
<div style="text-align: center; margin: 0.3rem 0 0.8rem;">
    <span style="color: %(accent)s; font-size: 1.2rem;">✦ ✦ ✦</span>
</div>
""" % {"accent": theme["accent"]}

    return html
