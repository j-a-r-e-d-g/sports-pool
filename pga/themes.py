# themes.py
# Modern dark dashboard theming for the sports pool platform.
# Consistent dark UI across all pages — tournament identity comes from
# an accent color and optional logo image in the header.

# ---------- Presets ----------
# Each preset has an accent color (used for highlights, active tabs,
# table headers) and an optional logo_url for the header.

PRESETS = {
    "masters": {
        "name": "The Masters",
        "accent": "#2D8B4E",
        "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/1/1b/Masters_Tournament_logo.svg/330px-Masters_Tournament_logo.svg.png",
    },
    "rbc_heritage": {
        "name": "RBC Heritage",
        "accent": "#E31837",
        "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/7/7a/RBC_Heritage_logo.png/330px-RBC_Heritage_logo.png",
    },
    "pga_championship": {
        "name": "PGA Championship",
        "accent": "#CFB53B",
        "logo_url": "",
    },
    "us_open": {
        "name": "US Open",
        "accent": "#003366",
        "logo_url": "",
    },
    "the_open": {
        "name": "The Open",
        "accent": "#C8A951",
        "logo_url": "",
    },
    "the_players": {
        "name": "THE PLAYERS",
        "accent": "#003057",
        "logo_url": "",
    },
    "memorial": {
        "name": "the Memorial Tournament",
        "accent": "#1A3C34",
        "logo_url": "",
    },
    "default": {
        "name": "Default",
        "accent": "#4A90D9",
        "logo_url": "",
    },
}

# ---------- Base palette (never changes) ----------
BG = "#0E1117"
BG_CARD = "#1A1D23"
BG_HOVER = "#22262E"
BORDER = "#2A2E35"
TEXT = "#E6E6E6"
TEXT_DIM = "#8B8D93"
TEXT_MUTED = "#5A5C63"

DEFAULT_THEME = PRESETS["default"]


def get_theme(tournament=None):
    """Get the theme for a tournament. Falls back to default."""
    if tournament and tournament.get("theme"):
        theme = tournament["theme"]
        if "accent" not in theme:
            theme["accent"] = DEFAULT_THEME["accent"]
        return theme
    return DEFAULT_THEME


def theme_css(theme):
    """
    Generate page-level CSS. Applied via st.markdown(unsafe_allow_html=True).
    """
    accent = theme.get("accent", DEFAULT_THEME["accent"])

    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp { background-color: %(bg)s; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: %(bg_card)s; border-radius: 8px; padding: 0.3rem;
        border: 1px solid %(border)s;
    }
    .stTabs [data-baseweb="tab"] {
        color: %(text_dim)s; font-family: 'Inter', sans-serif;
        font-size: 0.9rem; font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        color: %(accent)s !important;
        border-bottom-color: %(accent)s !important;
    }

    /* Labels */
    .stSelectbox label, .stTextInput label, .stNumberInput label,
    .stTextArea label { color: %(text_dim)s !important; }

    /* Sidebar — compact and clean */
    [data-testid="stSidebar"] { max-width: 180px; }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        padding-top: 1rem;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        font-size: 0.85rem;
    }

    /* Sidebar collapse button — more visible */
    [data-testid="stSidebar"] button[kind="header"] {
        color: #fff !important;
    }
    button[data-testid="stBaseButton-headerNoPadding"] {
        background-color: %(accent)s !important;
        color: #fff !important;
        border-radius: 0 8px 8px 0;
        padding: 0.4rem 0.5rem !important;
        opacity: 0.9;
    }
    button[data-testid="stBaseButton-headerNoPadding"]:hover {
        opacity: 1;
        background-color: %(accent)s !important;
    }
</style>
""" % {
        "bg": BG, "bg_card": BG_CARD, "border": BORDER,
        "text_dim": TEXT_DIM, "accent": accent,
    }


def shared_styles(theme):
    """
    Generate shared component styles for st.html() blocks.
    """
    accent = theme.get("accent", DEFAULT_THEME["accent"])

    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

    /* Score colors */
    .score-under { color: #E74C3C; font-weight: 700; }
    .score-over { color: %(text_dim)s; font-weight: 500; }
    .score-even { color: %(text)s; font-weight: 500; }
    .score-mc { color: #D4883A; font-style: italic; }
    .score-wd { color: #C0392B; font-style: italic; }

    /* Bonus badge */
    .bonus-badge {
        display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px;
        font-weight: 700; font-size: 0.78rem;
        background-color: rgba(74, 144, 217, 0.15); color: %(accent)s;
        border: 1px solid %(accent)s;
    }
    .bonus-none { color: %(text_muted)s; font-size: 0.8rem; }

    /* Pick indicators */
    .picked-tag {
        display: inline-block; padding: 0.1rem 0.4rem; border-radius: 4px;
        font-size: 0.72rem; font-weight: 600; margin: 1px;
        background-color: rgba(46, 204, 113, 0.12); color: #2ECC71;
        border: 1px solid rgba(46, 204, 113, 0.3);
    }
    .tier-tag {
        display: inline-block; padding: 0.05rem 0.3rem; border-radius: 3px;
        font-size: 0.65rem; font-weight: 600; margin-left: 2px;
        background-color: rgba(243, 156, 18, 0.12); color: #F39C12;
    }

    /* Rank badges */
    .rank-badge {
        display: inline-block;
        width: 28px; height: 28px; line-height: 28px;
        text-align: center; border-radius: 50%%;
        font-weight: 700; font-size: 0.85rem;
    }
    .rank-1 { background-color: #FFD700; color: #1a1a1a; }
    .rank-2 { background-color: #C0C0C0; color: #1a1a1a; }
    .rank-3 { background-color: #CD7F32; color: #fff; }
    .rank-other { background-color: %(bg_hover)s; color: %(text_dim)s; }

    /* Cards */
    .scoreboard {
        background-color: %(bg_card)s; border-radius: 10px;
        padding: 1.2rem; border: 1px solid %(border)s; color: %(text)s;
    }
    .scoreboard h3 {
        color: %(text)s; font-family: 'Inter', sans-serif;
        font-size: 1.1rem; font-weight: 600;
        border-bottom: 2px solid %(accent)s;
        padding-bottom: 0.4rem; margin-bottom: 0.8rem;
    }

    /* Tables */
    .leaderboard-table { width: 100%%; border-collapse: collapse; font-size: 0.9rem; }
    .leaderboard-table th {
        background-color: %(accent)s; color: #fff;
        padding: 0.55rem 0.8rem; text-align: left;
        font-family: 'Inter', sans-serif; font-size: 0.85rem;
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
    }
    .leaderboard-table td {
        padding: 0.5rem 0.8rem; border-bottom: 1px solid %(border)s; color: %(text)s;
    }
    .leaderboard-table tr:hover { background-color: %(bg_hover)s; }
    .leader-row { background-color: rgba(255, 215, 0, 0.06); font-weight: 600; }

    /* Detail cards */
    .detail-card {
        background-color: %(bg_card)s; border-radius: 10px;
        padding: 1rem 1.2rem; margin-bottom: 0.8rem;
        border: 1px solid %(border)s; color: %(text)s;
    }
    .detail-card h4 {
        color: %(text)s; font-family: 'Inter', sans-serif;
        margin: 0 0 0.6rem 0; font-size: 1rem; font-weight: 600;
    }
    .detail-table { width: 100%%; border-collapse: collapse; font-size: 0.82rem; }
    .detail-table th {
        background-color: %(accent)s; color: #fff;
        padding: 0.4rem 0.6rem; text-align: left; font-size: 0.78rem;
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px;
    }
    .detail-table td {
        padding: 0.4rem 0.6rem; border-bottom: 1px solid %(border)s; color: %(text)s;
    }

    /* Rules card */
    .rules-card {
        background-color: %(bg_card)s; border-radius: 10px;
        padding: 1.5rem; border: 1px solid %(border)s; color: %(text)s;
    }
    .rules-card h3 {
        color: %(text)s; font-family: 'Inter', sans-serif;
        font-size: 1rem; font-weight: 600;
        border-bottom: 2px solid %(accent)s;
        padding-bottom: 0.4rem; margin-bottom: 0.8rem;
    }
    .rules-card h3:first-child { margin-top: 0; }
    .rules-card p { margin: 0.5rem 0; line-height: 1.6; color: %(text_dim)s; }
    .rules-card table {
        width: 100%%; border-collapse: collapse; margin: 0.8rem 0 1.2rem;
    }
    .rules-card th {
        background-color: %(accent)s; color: #fff;
        padding: 0.5rem 0.8rem; text-align: left;
        font-size: 0.82rem; font-weight: 600; text-transform: uppercase;
    }
    .rules-card td {
        padding: 0.5rem 0.8rem; border-bottom: 1px solid %(border)s; color: %(text)s;
    }

    /* Winner banner */
    .winner-banner {
        background: linear-gradient(135deg, %(bg_card)s 0%%, %(bg)s 100%%);
        border: 2px solid %(accent)s; border-radius: 10px;
        padding: 1rem; text-align: center; margin-bottom: 1rem;
    }
    .winner-banner span {
        color: %(accent)s; font-family: 'Inter', sans-serif;
        font-size: 1.1rem; font-weight: 600;
    }

    @media (max-width: 768px) {
        .leaderboard-table { font-size: 0.8rem; }
        .leaderboard-table th, .leaderboard-table td { padding: 0.4rem; }
        .rank-badge { width: 24px; height: 24px; line-height: 24px; font-size: 0.75rem; }
    }
</style>
""" % {
        "bg": BG, "bg_card": BG_CARD, "bg_hover": BG_HOVER,
        "border": BORDER, "text": TEXT, "text_dim": TEXT_DIM,
        "text_muted": TEXT_MUTED, "accent": accent,
    }


def header_html(theme, title, subtitle="", logo_url=""):
    """Generate the page header with optional tournament logo."""
    accent = theme.get("accent", DEFAULT_THEME["accent"])
    logo = logo_url or theme.get("logo_url", "")

    html = ""
    if logo:
        html += """
<div style="text-align: center; padding: 1.5rem 0 0.5rem;">
    <img src="%s" alt="Tournament logo"
         style="max-height: 80px; max-width: 280px; object-fit: contain;
                filter: drop-shadow(0 2px 8px rgba(0,0,0,0.5));">
</div>
""" % logo

    html += """
<div style="text-align: center; padding: %s 0 0.3rem;">
    <h1 style="font-family: 'Inter', sans-serif; color: #fff;
               font-size: 1.8rem; font-weight: 700; letter-spacing: 1px;
               margin: 0;">
        %s
    </h1>
""" % ("0.5rem" if logo else "1.5rem", title)

    if subtitle:
        html += """
    <p style="color: %s; font-family: 'Inter', sans-serif;
              font-size: 0.9rem; margin-top: 0.3rem;">%s</p>
""" % (TEXT_DIM, subtitle)

    html += """
</div>
<div style="text-align: center; margin: 0.3rem 0 0.8rem;">
    <div style="width: 60px; height: 3px; background: %s;
                margin: 0 auto; border-radius: 2px;"></div>
</div>
""" % accent

    return html
