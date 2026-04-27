"""
AI-Powered Lost & Found System for Airport Operations
Main Streamlit Application — Premium UI/UX Edition

Pages:
1. Report Lost Item (Passenger View)
2. Register Found Item (Staff View)
3. Check Matches (Staff Dashboard)
4. Analytics Dashboard
5. Notifications (Simulation)
"""

import json
import os
from datetime import datetime
from uuid import uuid4

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_lottie import st_lottie

import ai_pipeline
import config
import database

# ─── App setup ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="SkyFind AI — Airport Lost & Found",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

database.init_db()
database.seed_demo_data()
os.makedirs(config.UPLOAD_DIR, exist_ok=True)

# ─── LUXURY CSS THEME ────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:wght@700;800;900&display=swap');

/* ══════════ ROOT THEME ══════════ */
:root {
    --gold: #D4A853;
    --gold-light: #F0D78C;
    --gold-dark: #B8860B;
    --dark-bg: #0A0E17;
    --card-bg: rgba(255, 255, 255, 0.03);
    --card-border: rgba(212, 168, 83, 0.15);
    --glass: rgba(255, 255, 255, 0.05);
    --text-primary: #F0F0F0;
    --text-secondary: #8B8FA3;
    --green: #00D68F;
    --yellow: #FFAA00;
    --red: #FF4757;
    --blue: #339AF0;
}

/* ══════════ GLOBAL STYLES ══════════ */
.stApp {
    background: linear-gradient(135deg, #0A0E17 0%, #141B2D 50%, #0D1321 100%);
    font-family: 'Inter', sans-serif;
}

.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse at 20% 50%, rgba(212, 168, 83, 0.04) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 20%, rgba(51, 154, 240, 0.03) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 80%, rgba(212, 168, 83, 0.02) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
}

/* ══════════ SIDEBAR ══════════ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1321 0%, #141B2D 100%) !important;
    border-right: 1px solid var(--card-border);
}

section[data-testid="stSidebar"] .stRadio > label {
    color: var(--text-secondary) !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 600;
}

section[data-testid="stSidebar"] .stRadio > div > label {
    background: var(--glass) !important;
    border: 1px solid transparent !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    margin-bottom: 6px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}

section[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(212, 168, 83, 0.1) !important;
    border-color: var(--gold) !important;
    transform: translateX(4px);
}

section[data-testid="stSidebar"] .stRadio > div [data-checked="true"] > label,
section[data-testid="stSidebar"] .stRadio > div label[data-checked="true"] {
    background: linear-gradient(135deg, rgba(212, 168, 83, 0.15), rgba(212, 168, 83, 0.05)) !important;
    border-color: var(--gold) !important;
    box-shadow: 0 0 20px rgba(212, 168, 83, 0.1);
}

/* ══════════ HEADINGS ══════════ */
h1 {
    font-family: 'Playfair Display', serif !important;
    background: linear-gradient(135deg, var(--gold-light), var(--gold), var(--gold-dark));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 900 !important;
    letter-spacing: -0.5px;
}

h2, h3 {
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
}

p, li, span, div {
    color: var(--text-secondary);
}

/* ══════════ GLASS CARDS ══════════ */
.glass-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--card-border);
    border-radius: 20px;
    padding: 28px;
    margin: 12px 0;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.glass-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--gold-light), transparent);
    opacity: 0.4;
}

.glass-card:hover {
    border-color: rgba(212, 168, 83, 0.3);
    transform: translateY(-2px);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 40px rgba(212, 168, 83, 0.05);
}

/* ══════════ 3D METRIC CARDS ══════════ */
.metric-card {
    background: linear-gradient(145deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
    border: 1px solid var(--card-border);
    border-radius: 20px;
    padding: 24px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    transform-style: preserve-3d;
    perspective: 1000px;
}

.metric-card:hover {
    transform: translateY(-8px) rotateX(2deg);
    box-shadow:
        0 25px 50px rgba(0, 0, 0, 0.4),
        0 0 30px rgba(212, 168, 83, 0.08),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
    border-color: var(--gold);
}

.metric-card .metric-icon {
    font-size: 2.2rem;
    margin-bottom: 8px;
    display: block;
    filter: drop-shadow(0 0 10px rgba(212, 168, 83, 0.3));
}

.metric-card .metric-value {
    font-family: 'Playfair Display', serif;
    font-size: 2.8rem;
    font-weight: 900;
    background: linear-gradient(135deg, var(--gold-light), var(--gold));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
    margin: 4px 0;
}

.metric-card .metric-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-secondary);
    font-weight: 600;
}

/* ══════════ CONFIDENCE BAR ══════════ */
.confidence-bar-wrapper {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 3px;
    margin: 8px 0;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.confidence-bar {
    height: 28px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    color: #fff;
    transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

.confidence-bar::after {
    content: '';
    position: absolute;
    top: 0; left: -100%; right: 0; bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    animation: shimmer 2s ease-in-out infinite;
}

@keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
}

.confidence-high {
    background: linear-gradient(135deg, #00D68F, #00B87A);
    box-shadow: 0 0 20px rgba(0, 214, 143, 0.3);
}

.confidence-medium {
    background: linear-gradient(135deg, #FFAA00, #FF8C00);
    box-shadow: 0 0 20px rgba(255, 170, 0, 0.3);
}

.confidence-low {
    background: linear-gradient(135deg, #FF4757, #FF3344);
    box-shadow: 0 0 20px rgba(255, 71, 87, 0.3);
}

/* ══════════ HERO HEADER ══════════ */
.hero-header {
    text-align: center;
    padding: 40px 20px 30px;
    position: relative;
}

.hero-header h1 {
    font-size: 3rem !important;
    margin-bottom: 8px;
}

.hero-subtitle {
    font-size: 1.05rem;
    color: var(--text-secondary);
    font-weight: 300;
    letter-spacing: 0.5px;
    max-width: 600px;
    margin: 0 auto;
}

/* ══════════ FORMS ══════════ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    transition: all 0.3s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--gold) !important;
    box-shadow: 0 0 20px rgba(212, 168, 83, 0.1) !important;
}

/* ══════════ BUTTONS ══════════ */
.stButton > button {
    background: linear-gradient(135deg, var(--gold-dark), var(--gold), var(--gold-light)) !important;
    color: #0A0E17 !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 12px 32px !important;
    letter-spacing: 0.5px !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-transform: uppercase;
    box-shadow: 0 4px 15px rgba(212, 168, 83, 0.2) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow: 0 8px 30px rgba(212, 168, 83, 0.35) !important;
}

.stButton > button:active {
    transform: translateY(0) scale(0.98) !important;
}

/* ══════════ EXPANDER ══════════ */
.streamlit-expanderHeader {
    background: var(--glass) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 14px !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    transition: all 0.3s ease !important;
}

.streamlit-expanderHeader:hover {
    border-color: var(--gold) !important;
    background: rgba(212, 168, 83, 0.05) !important;
}

/* ══════════ DATAFRAMES ══════════ */
.stDataFrame {
    border-radius: 16px !important;
    overflow: hidden;
    border: 1px solid var(--card-border) !important;
}

/* ══════════ DIVIDER ══════════ */
hr {
    border-color: var(--card-border) !important;
    opacity: 0.5;
}

/* ══════════ STATUS BADGE ══════════ */
.status-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}

.badge-active { background: rgba(0, 214, 143, 0.15); color: #00D68F; border: 1px solid rgba(0, 214, 143, 0.3); }
.badge-pending { background: rgba(255, 170, 0, 0.15); color: #FFAA00; border: 1px solid rgba(255, 170, 0, 0.3); }
.badge-matched { background: rgba(51, 154, 240, 0.15); color: #339AF0; border: 1px solid rgba(51, 154, 240, 0.3); }
.badge-closed { background: rgba(255, 255, 255, 0.08); color: var(--text-secondary); border: 1px solid rgba(255,255,255,0.1); }

/* ══════════ ANIMATED FLOATING PARTICLES ══════════ */
.particles {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
}

.particle {
    position: absolute;
    width: 3px;
    height: 3px;
    background: var(--gold);
    border-radius: 50%;
    opacity: 0;
    animation: float-up 8s ease-in-out infinite;
}

@keyframes float-up {
    0% { opacity: 0; transform: translateY(100vh) scale(0); }
    20% { opacity: 0.6; }
    80% { opacity: 0.2; }
    100% { opacity: 0; transform: translateY(-10vh) scale(1); }
}

/* ══════════ MATCH COMPARISON CARD ══════════ */
.match-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
    border: 1px solid var(--card-border);
    border-radius: 20px;
    padding: 24px;
    margin: 16px 0;
    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    transform-style: preserve-3d;
}

.match-card:hover {
    transform: perspective(1000px) rotateY(-1deg) rotateX(1deg) translateY(-4px);
    box-shadow: 0 30px 60px rgba(0,0,0,0.3), 0 0 40px rgba(212, 168, 83, 0.06);
    border-color: rgba(212, 168, 83, 0.3);
}

/* ══════════ GLOW TEXT ══════════ */
.glow-text {
    color: var(--gold);
    text-shadow: 0 0 10px rgba(212, 168, 83, 0.3), 0 0 40px rgba(212, 168, 83, 0.1);
}

/* ══════════ NOTIFICATION CARD ══════════ */
.notif-card {
    background: linear-gradient(135deg, rgba(51, 154, 240, 0.05), rgba(255,255,255,0.02));
    border: 1px solid rgba(51, 154, 240, 0.15);
    border-radius: 16px;
    padding: 20px;
    margin: 10px 0;
    transition: all 0.3s ease;
}

.notif-card:hover {
    border-color: rgba(51, 154, 240, 0.4);
    transform: translateX(4px);
}

/* ══════════ PLOTLY OVERRIDE ══════════ */
.js-plotly-plot .plotly .modebar { display: none !important; }
</style>

<!-- Floating Particles Background -->
<div class="particles">
    <div class="particle" style="left:10%;animation-delay:0s;animation-duration:7s"></div>
    <div class="particle" style="left:20%;animation-delay:1.5s;animation-duration:9s"></div>
    <div class="particle" style="left:35%;animation-delay:3s;animation-duration:6s"></div>
    <div class="particle" style="left:50%;animation-delay:0.5s;animation-duration:8s"></div>
    <div class="particle" style="left:65%;animation-delay:2s;animation-duration:10s"></div>
    <div class="particle" style="left:78%;animation-delay:4s;animation-duration:7.5s"></div>
    <div class="particle" style="left:88%;animation-delay:1s;animation-duration:9.5s"></div>
    <div class="particle" style="left:5%;animation-delay:5s;animation-duration:6.5s"></div>
    <div class="particle" style="left:42%;animation-delay:3.5s;animation-duration:8.5s"></div>
    <div class="particle" style="left:95%;animation-delay:2.5s;animation-duration:7s"></div>
</div>
""", unsafe_allow_html=True)


# ─── Lottie animations ───────────────────────────────────────────────

LOTTIE_URLS = {
    "airplane": {"v":"5.5.7","fr":30,"ip":0,"op":60,"w":200,"h":200,"nm":"plane","layers":[{"ty":4,"nm":"plane","sr":1,"ks":{"o":{"a":0,"k":100},"r":{"a":1,"k":[{"i":{"x":[0.4],"y":[1]},"o":{"x":[0.6],"y":[0]},"t":0,"s":[0]},{"t":60,"s":[360]}]},"p":{"a":0,"k":[100,100]},"s":{"a":0,"k":[100,100]}},"shapes":[{"ty":"gr","it":[{"ty":"sr","p":{"a":0,"k":[0,0]},"or":{"a":0,"k":60},"ir":{"a":0,"k":30},"r":{"a":0,"k":0},"pt":{"a":0,"k":4},"s":{"a":0,"k":0},"nm":"star"},{"ty":"fl","c":{"a":0,"k":[0.83,0.66,0.33,1]},"o":{"a":0,"k":60},"nm":"fill"},{"ty":"tr","p":{"a":0,"k":[0,0]},"a":{"a":0,"k":[0,0]},"s":{"a":0,"k":[100,100]},"r":{"a":0,"k":0},"o":{"a":0,"k":100}}],"nm":"grp"}],"ip":0,"op":60,"st":0}]},
    "search": {"v":"5.5.7","fr":30,"ip":0,"op":90,"w":150,"h":150,"nm":"srch","layers":[{"ty":4,"nm":"c","sr":1,"ks":{"o":{"a":0,"k":100},"r":{"a":0,"k":0},"p":{"a":0,"k":[75,75]},"s":{"a":1,"k":[{"i":{"x":[0.4],"y":[1]},"o":{"x":[0.6],"y":[0]},"t":0,"s":[90,90]},{"i":{"x":[0.4],"y":[1]},"o":{"x":[0.6],"y":[0]},"t":45,"s":[110,110]},{"t":90,"s":[90,90]}]}},"shapes":[{"ty":"gr","it":[{"ty":"el","p":{"a":0,"k":[0,0]},"s":{"a":0,"k":[80,80]},"nm":"el"},{"ty":"st","c":{"a":0,"k":[0.83,0.66,0.33,1]},"o":{"a":0,"k":100},"w":{"a":0,"k":4},"nm":"strk"},{"ty":"tr","p":{"a":0,"k":[0,0]},"a":{"a":0,"k":[0,0]},"s":{"a":0,"k":[100,100]},"r":{"a":0,"k":0},"o":{"a":0,"k":100}}],"nm":"grp"}],"ip":0,"op":90,"st":0}]},
}


def render_lottie(key: str, height: int = 120):
    """Render a Lottie animation."""
    if key in LOTTIE_URLS:
        st_lottie(LOTTIE_URLS[key], height=height, key=f"lottie_{key}_{id(key)}")


# ─── Helper components ───────────────────────────────────────────────

def render_hero(title: str, subtitle: str, icon: str = ""):
    """Render a premium hero header."""
    st.markdown(f"""
    <div class="hero-header">
        <div style="font-size:3.5rem;margin-bottom:10px;filter:drop-shadow(0 0 15px rgba(212,168,83,0.3))">{icon}</div>
        <h1>{title}</h1>
        <p class="hero-subtitle">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(icon: str, value: str, label: str):
    """Render a 3D metric card."""
    st.markdown(f"""
    <div class="metric-card">
        <span class="metric-icon">{icon}</span>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_confidence_bar(score: float):
    """Render an animated confidence bar with shimmer effect."""
    pct = int(score * 100)
    if score >= 0.85:
        css_class = "confidence-high"
    elif score >= 0.60:
        css_class = "confidence-medium"
    else:
        css_class = "confidence-low"

    st.markdown(f"""
    <div class="confidence-bar-wrapper">
        <div class="confidence-bar {css_class}" style="width:{pct}%">
            {pct}%
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_status_badge(status: str):
    """Render a colored status badge."""
    badge_map = {
        "active": "badge-active", "unclaimed": "badge-active",
        "pending": "badge-pending",
        "matched": "badge-matched", "confirmed": "badge-matched",
        "closed": "badge-closed", "rejected": "badge-closed", "claimed": "badge-closed",
    }
    css = badge_map.get(status, "badge-pending")
    return f'<span class="status-badge {css}">{status}</span>'


def render_glass_card(content: str):
    """Wrap content in a glass card."""
    st.markdown(f'<div class="glass-card">{content}</div>', unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:20px 0 10px">
        <div style="font-size:2.8rem;filter:drop-shadow(0 0 20px rgba(212,168,83,0.4))">✈️</div>
        <h1 style="font-size:1.6rem !important;margin:8px 0 2px">SkyFind AI</h1>
        <p style="font-size:0.75rem;text-transform:uppercase;letter-spacing:3px;color:#8B8FA3;margin:0">
            Airport Lost & Found
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    mode_text = "🟢 LIVE MODE" if not config.is_demo_mode() else "🔧 DEMO MODE"
    mode_color = "rgba(0,214,143,0.1)" if not config.is_demo_mode() else "rgba(255,170,0,0.1)"
    mode_border = "rgba(0,214,143,0.3)" if not config.is_demo_mode() else "rgba(255,170,0,0.3)"
    st.markdown(f"""
    <div style="background:{mode_color};border:1px solid {mode_border};border-radius:12px;
                padding:10px;text-align:center;margin:0 0 16px">
        <span style="font-size:0.8rem;font-weight:600;letter-spacing:1px">{mode_text}</span>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "NAVIGATION",
        ["✈️  Report Lost Item",
         "📦  Register Found Item",
         "🔍  Match Dashboard",
         "📊  Analytics",
         "🔔  Notifications"],
        label_visibility="visible",
    )

    st.markdown("""
    <div style="position:absolute;bottom:20px;left:20px;right:20px;text-align:center">
        <p style="font-size:0.65rem;color:#555;letter-spacing:1px">
            POWERED BY AZURE AI<br>GBG GROUP B — NTI ACADEMY
        </p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 1: REPORT LOST ITEM
# ═══════════════════════════════════════════════════════════════════

def page_report_lost_item():
    render_hero("Report Lost Item", "Tell us what you lost — our AI will find it for you", "🧳")

    with st.form("lost_item_form", clear_on_submit=True):
        st.markdown("##### 👤 Personal Information")
        col1, col2, col3 = st.columns(3)
        with col1:
            passenger_name = st.text_input("Full Name", placeholder="Ahmed Hassan")
        with col2:
            contact_email = st.text_input("Email Address", placeholder="ahmed@email.com")
        with col3:
            contact_phone = st.text_input("Phone Number", placeholder="+201001234567")

        st.markdown("---")
        st.markdown("##### 📝 Item Details")
        col_a, col_b = st.columns(2)
        with col_a:
            item_category = st.selectbox("Category", [
                "phone", "laptop", "tablet", "wallet", "bag", "luggage", "watch",
                "jewelry", "passport", "keys", "headphones", "camera", "clothing",
                "book", "glasses", "umbrella", "charger", "other",
            ])
            item_color = st.text_input("Color", placeholder="e.g. black, silver, navy blue")
            item_brand = st.text_input("Brand", placeholder="e.g. Apple, Samsung, Rolex")
        with col_b:
            location_last_seen = st.selectbox("Last Seen Location", [
                "", "Terminal 1", "Terminal 2", "Terminal 3", "Gates A", "Gates B",
                "Gates C", "Aircraft", "Security", "Baggage Claim", "Lounge",
                "Restroom", "Food Court", "Parking",
            ])
            time_last_seen = st.date_input("Date Last Seen")
            photo = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])

        item_description = st.text_area(
            "Describe your item in detail",
            placeholder="e.g. Black leather wallet with gold initials 'AH' engraved on front. Contains credit cards and Egyptian ID.",
            height=120,
            max_chars=1000,
        )

        submitted = st.form_submit_button("✈️  SUBMIT REPORT", use_container_width=True)

    if submitted:
        if not passenger_name or not contact_email or not item_description:
            st.error("Please fill in Name, Email, and Description.")
            return
        if "@" not in contact_email or "." not in contact_email:
            st.error("Please enter a valid email address.")
            return
        if len(item_description.strip()) < 10:
            st.error("Please provide a more detailed description (at least 10 characters).")
            return

        photo_path = None
        if photo:
            photo_path = os.path.join(config.UPLOAD_DIR, f"{uuid4()}_{photo.name}")
            with open(photo_path, "wb") as f:
                f.write(photo.getbuffer())

        with st.spinner("🤖 AI is analyzing your description..."):
            try:
                attributes = ai_pipeline.extract_item_attributes(item_description)
            except Exception as e:
                st.error(f"AI analysis failed: {e}. Submitting with manual data only.")
                attributes = {"category": item_category, "color": item_color, "brand": item_brand}

        case_id = str(uuid4())
        database.insert_lost_report({
            "case_id": case_id, "passenger_name": passenger_name,
            "contact_email": contact_email, "contact_phone": contact_phone,
            "item_description": item_description, "item_category": item_category,
            "item_color": item_color or attributes.get("color", ""),
            "item_brand": item_brand or attributes.get("brand", ""),
            "location_last_seen": location_last_seen,
            "time_last_seen": str(time_last_seen), "optional_photo_path": photo_path,
            "status": "active", "created_at": datetime.utcnow().isoformat(),
        })

        st.markdown(f"""
        <div class="glass-card" style="text-align:center;border-color:rgba(0,214,143,0.3)">
            <div style="font-size:3rem;margin-bottom:10px">✅</div>
            <h3 style="color:#00D68F !important">Report Submitted Successfully</h3>
            <p style="font-size:0.85rem;color:#8B8FA3;margin:12px 0">Your Case ID</p>
            <p style="font-family:monospace;font-size:1rem;color:var(--gold);background:rgba(212,168,83,0.1);
                      display:inline-block;padding:8px 20px;border-radius:10px;border:1px solid rgba(212,168,83,0.2)">
                {case_id[:8]}...{case_id[-4:]}
            </p>
            <p style="font-size:0.8rem;color:#555;margin-top:12px">Save this ID — we'll notify you when a match is found</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 AI-Extracted Attributes"):
            st.json(attributes)


# ═══════════════════════════════════════════════════════════════════
# PAGE 2: REGISTER FOUND ITEM
# ═══════════════════════════════════════════════════════════════════

def page_register_found_item():
    render_hero("Register Found Item", "Upload a photo and let AI do the rest", "📦")

    with st.form("found_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            staff_id = st.text_input("Staff ID", placeholder="STAFF-101")
            location_found = st.selectbox("Location Found", [
                "Terminal 1", "Terminal 2", "Terminal 3", "Gates A", "Gates B",
                "Gates C", "Aircraft", "Security", "Baggage Claim", "Lounge",
                "Restroom", "Food Court", "Parking",
            ])
        with col2:
            time_found = st.date_input("Date Found")
            optional_notes = st.text_area("Notes", placeholder="Found under seat at gate B7", height=100)

        photo = st.file_uploader("📸 Upload Item Photo (Required)", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("📦  REGISTER FOUND ITEM", use_container_width=True)

    if submitted:
        if not staff_id:
            st.error("Please enter your Staff ID.")
            return
        if not photo:
            st.error("Photo is required.")
            return

        photo_path = os.path.join(config.UPLOAD_DIR, f"{uuid4()}_{photo.name}")
        with open(photo_path, "wb") as f:
            f.write(photo.getbuffer())

        with st.spinner("🤖 AI is analyzing the photo..."):
            try:
                image_analysis = ai_pipeline.analyze_item_image(photo_path)
            except Exception as e:
                st.warning(f"Image analysis failed ({e}). Using basic registration.")
                image_analysis = {"caption": "", "tags": [], "ocr_text": "", "objects": []}

        c1, c2 = st.columns(2)
        with c1:
            st.image(photo_path, caption="Uploaded Photo", use_container_width=True)
        with c2:
            render_glass_card(f"""
            <h3 style="margin-top:0">📸 AI Analysis</h3>
            <p><strong style="color:{('#D4A853')}">Caption:</strong> {image_analysis.get('caption', 'N/A')}</p>
            <p><strong style="color:{('#D4A853')}">Tags:</strong> {', '.join(image_analysis.get('tags', [])[:6])}</p>
            <p><strong style="color:{('#D4A853')}">OCR Text:</strong> {image_analysis.get('ocr_text', 'None')}</p>
            <p><strong style="color:{('#D4A853')}">Objects:</strong> {', '.join(image_analysis.get('objects', []))}</p>
            """)

        caption = image_analysis.get("caption", "")
        tags = image_analysis.get("tags", [])
        ocr_text = image_analysis.get("ocr_text", "")
        auto_desc = caption + (f" Tags: {', '.join(tags[:5])}." if tags else "") + \
                    (f" Text: {ocr_text}." if ocr_text else "") + \
                    (f" Notes: {optional_notes}" if optional_notes else "")

        with st.spinner("🤖 Extracting attributes..."):
            try:
                attributes = ai_pipeline.extract_item_attributes(auto_desc)
                embedding = ai_pipeline.generate_embedding(attributes.get("normalized_description", auto_desc))
            except Exception as e:
                st.warning(f"AI extraction failed ({e}). Using defaults.")
                attributes = {"category": "other", "color": "", "brand": "", "normalized_description": auto_desc}
                embedding = ai_pipeline._mock_embedding(auto_desc)

        found_id = str(uuid4())
        item_data = {
            "found_id": found_id, "staff_id": staff_id, "item_description": auto_desc,
            "item_category": attributes.get("category", "other"),
            "item_color": attributes.get("color", ""), "item_brand": attributes.get("brand", ""),
            "location_found": location_found, "time_found": str(time_found),
            "photo_path": photo_path, "optional_notes": optional_notes,
            "status": "unclaimed", "created_at": datetime.utcnow().isoformat(),
        }
        database.insert_found_item(item_data)
        ai_pipeline.index_found_item(item_data, attributes, embedding)

        st.markdown(f"""
        <div class="glass-card" style="text-align:center;border-color:rgba(0,214,143,0.3)">
            <div style="font-size:3rem;margin-bottom:10px">✅</div>
            <h3 style="color:#00D68F !important">Item Registered & Indexed</h3>
            <p style="font-family:monospace;color:var(--gold)">{found_id[:8]}...{found_id[-4:]}</p>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 3: MATCH DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def page_check_matches():
    render_hero("Match Dashboard", "AI-powered matching engine — find the owner", "🔍")

    # Existing matches
    all_matches = database.get_all_match_results()
    if all_matches:
        st.markdown("### 📋 Match History")
        for match in all_matches:
            score = match["confidence_score"]
            lost = database.get_lost_report(match["lost_case_id"])
            found = database.get_found_item(match["found_item_id"])
            if not lost or not found:
                continue

            status_html = render_status_badge(match["status"])
            with st.expander(f"{'🟢' if score >= 0.85 else '🟡' if score >= 0.6 else '🔴'} {score:.0%} — {lost['item_description'][:40]}... {status_html}", expanded=False):
                render_confidence_bar(score)
                c1, c2 = st.columns(2)
                with c1:
                    render_glass_card(f"""
                    <h4 style="color:#FF6B6B;margin-top:0">🧳 Lost Item</h4>
                    <p><strong>Passenger:</strong> {lost['passenger_name']}</p>
                    <p><strong>Description:</strong> {lost['item_description'][:100]}</p>
                    <p><strong>Category:</strong> {lost['item_category']} · <strong>Color:</strong> {lost['item_color']}</p>
                    """)
                with c2:
                    render_glass_card(f"""
                    <h4 style="color:#00D68F;margin-top:0">📦 Found Item</h4>
                    <p><strong>Description:</strong> {found['item_description'][:100]}</p>
                    <p><strong>Category:</strong> {found['item_category']} · <strong>Color:</strong> {found['item_color']}</p>
                    <p><strong>Location:</strong> {found['location_found']}</p>
                    """)

                if match["status"] == "pending":
                    bc1, bc2, _ = st.columns([1, 1, 2])
                    if bc1.button("✅ Confirm", key=f"c_{match['match_id']}"):
                        database.update_match_status(match["match_id"], "confirmed", "staff")
                        database.update_lost_report_status(match["lost_case_id"], "matched")
                        database.update_found_item_status(match["found_item_id"], "matched")
                        database.insert_notification({
                            "case_id": match["lost_case_id"], "match_id": match["match_id"],
                            "passenger_email": lost["contact_email"], "confidence_score": score,
                            "found_item_description": found["item_description"],
                            "message": f"Great news! We found your item. Confidence: {score:.0%}.",
                        })
                        st.rerun()
                    if bc2.button("❌ Reject", key=f"r_{match['match_id']}"):
                        database.update_match_status(match["match_id"], "rejected", "staff")
                        st.rerun()
        st.markdown("---")

    # Active lost reports
    st.markdown("### 🧳 Active Lost Reports")
    lost_reports = database.get_all_lost_reports(status_filter="active")
    found_items = database.get_all_found_items(status_filter="unclaimed")

    if not lost_reports:
        render_glass_card("<p style='text-align:center;color:#8B8FA3'>No active reports. Reports appear here when passengers submit them.</p>")
        return

    for report in lost_reports:
        cat_icons = {"wallet": "👛", "laptop": "💻", "phone": "📱", "watch": "⌚", "luggage": "🧳",
                     "headphones": "🎧", "keys": "🔑", "passport": "🛂", "bag": "👜", "camera": "📷",
                     "jewelry": "💍", "glasses": "👓", "umbrella": "☂️"}
        icon = cat_icons.get(report["item_category"], "📋")

        with st.expander(f"{icon} {report['item_category'].upper()} — {report['item_description'][:55]}..."):
            render_glass_card(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">
                <div>
                    <h4 style="margin:0;color:#F0F0F0">{report['passenger_name']}</h4>
                    <p style="font-size:0.8rem;margin:2px 0">{report['contact_email']}</p>
                </div>
                <div>{render_status_badge(report['status'])}</div>
            </div>
            <hr style="border-color:rgba(255,255,255,0.05);margin:12px 0">
            <p style="color:#F0F0F0">{report['item_description']}</p>
            <p style="font-size:0.85rem">
                <strong style="color:#D4A853">Category:</strong> {report['item_category']} ·
                <strong style="color:#D4A853">Color:</strong> {report['item_color']} ·
                <strong style="color:#D4A853">Brand:</strong> {report['item_brand']} ·
                <strong style="color:#D4A853">Location:</strong> {report['location_last_seen']}
            </p>
            """)

            if st.button(f"🔍  RUN AI MATCH", key=f"match_{report['case_id']}", use_container_width=True):
                if not found_items:
                    st.warning("No unclaimed found items to match against.")
                else:
                    with st.spinner("🤖 AI is searching for matches..."):
                        try:
                            matches = ai_pipeline.find_matches(report, found_items)
                        except Exception as e:
                            st.error(f"Matching failed: {e}")
                            matches = []

                    if not matches:
                        render_glass_card("<p style='text-align:center'>No matches found.</p>")
                    else:
                        for i, match in enumerate(matches):
                            score = match["confidence_score"]
                            found = database.get_found_item(match["found_item_id"])
                            if not found:
                                continue

                            emoji = "🟢" if score >= 0.85 else "🟡" if score >= 0.6 else "🔴"
                            st.markdown(f"#### {emoji} Match #{i+1}")
                            render_confidence_bar(score)

                            mc1, mc2 = st.columns(2)
                            with mc1:
                                render_glass_card(f"""
                                <h4 style="color:#FF6B6B;margin-top:0">🧳 Lost (Passenger)</h4>
                                <p style="color:#F0F0F0">{report['item_description']}</p>
                                """)
                            with mc2:
                                render_glass_card(f"""
                                <h4 style="color:#00D68F;margin-top:0">📦 Found (Staff)</h4>
                                <p style="color:#F0F0F0">{found['item_description']}</p>
                                """)
                                if found.get("photo_path") and os.path.exists(found["photo_path"]):
                                    st.image(found["photo_path"], width=200)

                            reasoning = match.get("reasoning", "N/A")
                            reasons = match.get("match_reasons", [])
                            render_glass_card(f"""
                            <h4 style="color:#D4A853;margin-top:0">🧠 AI Reasoning</h4>
                            <p style="color:#F0F0F0;font-size:0.9rem">{reasoning}</p>
                            {'<p style="color:#8B8FA3;font-size:0.85rem"><strong>Factors:</strong> ' + ' · '.join(reasons) + '</p>' if reasons else ''}
                            """)

                            b1, b2, _ = st.columns([1, 1, 2])
                            if b1.button("✅ Confirm", key=f"cn_{report['case_id']}_{match['found_item_id']}"):
                                database.insert_match_result({
                                    "match_id": match["match_id"], "lost_case_id": report["case_id"],
                                    "found_item_id": match["found_item_id"], "confidence_score": score,
                                    "match_reasons": json.dumps(reasons), "status": "confirmed",
                                    "reviewed_by": "staff", "reviewed_at": datetime.utcnow().isoformat(),
                                })
                                database.update_lost_report_status(report["case_id"], "matched")
                                database.update_found_item_status(match["found_item_id"], "matched")
                                database.insert_notification({
                                    "case_id": report["case_id"], "match_id": match["match_id"],
                                    "passenger_email": report["contact_email"], "confidence_score": score,
                                    "found_item_description": found["item_description"],
                                    "message": f"We found your item! Confidence: {score:.0%}. Visit Lost & Found.",
                                })
                                st.rerun()
                            if b2.button("❌ Reject", key=f"rj_{report['case_id']}_{match['found_item_id']}"):
                                database.insert_match_result({
                                    "match_id": match["match_id"], "lost_case_id": report["case_id"],
                                    "found_item_id": match["found_item_id"], "confidence_score": score,
                                    "match_reasons": json.dumps(reasons), "status": "rejected",
                                    "reviewed_by": "staff", "reviewed_at": datetime.utcnow().isoformat(),
                                })
                                st.info("Match rejected.")


# ═══════════════════════════════════════════════════════════════════
# PAGE 4: ANALYTICS DASHBOARD
# ═══════════════════════════════════════════════════════════════════

PLOTLY_DARK_TEMPLATE = dict(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8B8FA3"),
        title_font=dict(color="#F0F0F0", size=16),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.04)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", zerolinecolor="rgba(255,255,255,0.04)"),
        margin=dict(l=40, r=20, t=50, b=40),
    )
)


def page_analytics():
    render_hero("Analytics Dashboard", "Real-time insights into airport lost & found operations", "📊")

    lost_reports = database.get_all_lost_reports()
    found_items = database.get_all_found_items()
    matches = database.get_all_match_results()
    notifications = database.get_all_notifications()

    # KPI Cards
    active = len([r for r in lost_reports if r["status"] == "active"])
    unclaimed = len([f for f in found_items if f["status"] == "unclaimed"])
    confirmed = len([m for m in matches if m["status"] == "confirmed"])
    avg_conf = sum(m["confidence_score"] for m in matches) / len(matches) if matches else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_metric_card("🧳", str(active), "Open Cases")
    with k2:
        render_metric_card("📦", str(unclaimed), "Unclaimed Items")
    with k3:
        render_metric_card("✅", str(confirmed), "Confirmed Matches")
    with k4:
        render_metric_card("🎯", f"{avg_conf:.0%}", "Avg Confidence")

    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

    # Charts
    c1, c2 = st.columns(2)

    with c1:
        if lost_reports:
            df = pd.DataFrame(lost_reports)
            cat_counts = df["item_category"].value_counts().head(10).reset_index()
            cat_counts.columns = ["Category", "Count"]
            fig = go.Figure(go.Bar(
                x=cat_counts["Count"], y=cat_counts["Category"],
                orientation="h",
                marker=dict(
                    color=cat_counts["Count"],
                    colorscale=[[0, "#B8860B"], [0.5, "#D4A853"], [1, "#F0D78C"]],
                    cornerradius=8,
                ),
                text=cat_counts["Count"], textposition="auto",
                textfont=dict(color="#0A0E17", size=13, family="Inter"),
            ))
            fig.update_layout(
                **PLOTLY_DARK_TEMPLATE["layout"].to_plotly_json(),
                title="🏷️ Most Lost Item Categories",
                yaxis=dict(autorange="reversed", gridcolor="rgba(255,255,255,0.04)"),
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        if found_items:
            df = pd.DataFrame(found_items)
            loc_counts = df["location_found"].value_counts().head(8).reset_index()
            loc_counts.columns = ["Location", "Count"]
            fig = go.Figure(go.Bar(
                x=loc_counts["Count"], y=loc_counts["Location"],
                orientation="h",
                marker=dict(
                    color=loc_counts["Count"],
                    colorscale=[[0, "#FF4757"], [0.5, "#FF6B6B"], [1, "#FF8A8A"]],
                    cornerradius=8,
                ),
                text=loc_counts["Count"], textposition="auto",
                textfont=dict(color="#0A0E17", size=13, family="Inter"),
            ))
            fig.update_layout(
                **PLOTLY_DARK_TEMPLATE["layout"].to_plotly_json(),
                title="📍 High-Risk Zones",
                yaxis=dict(autorange="reversed", gridcolor="rgba(255,255,255,0.04)"),
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

    # Resolution time trend
    import random
    random.seed(42)
    dates = pd.date_range(end=datetime.utcnow(), periods=30, freq="D")
    hours = [max(1, random.uniform(2, 48) - i * 0.5) for i in range(30)]
    df_trend = pd.DataFrame({"Date": dates, "Hours": hours})

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_trend["Date"], y=df_trend["Hours"],
        mode="lines+markers",
        line=dict(color="#D4A853", width=3, shape="spline"),
        marker=dict(size=6, color="#D4A853", line=dict(color="#0A0E17", width=2)),
        fill="tozeroy",
        fillcolor="rgba(212, 168, 83, 0.05)",
    ))
    fig.update_layout(
        **PLOTLY_DARK_TEMPLATE["layout"].to_plotly_json(),
        title="⏱️ Average Resolution Time (Hours)",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary
    st.markdown("### 📋 Summary")
    summary = pd.DataFrame({
        "Metric": ["Total Lost Reports", "Total Found Items", "Matches Generated",
                    "Confirmed", "Rejected", "Pending", "Notifications Sent"],
        "Value": [len(lost_reports), len(found_items), len(matches),
                  len([m for m in matches if m["status"] == "confirmed"]),
                  len([m for m in matches if m["status"] == "rejected"]),
                  len([m for m in matches if m["status"] == "pending"]),
                  len(notifications)],
    })
    st.dataframe(summary, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 5: NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════

def page_notifications():
    render_hero("Notification Center", "Track all passenger notifications and communications", "🔔")

    notifications = database.get_all_notifications()

    if not notifications:
        render_glass_card("""
        <div style="text-align:center;padding:30px">
            <div style="font-size:3rem;margin-bottom:12px;opacity:0.5">🔔</div>
            <h3 style="color:#8B8FA3">No Notifications Yet</h3>
            <p style="color:#555">Notifications appear when matches are confirmed on the Match Dashboard</p>
        </div>
        """)

        st.markdown("---")
        st.markdown("### 📤 Simulate Notification")
        with st.form("sim_notif"):
            email = st.text_input("Passenger Email", value="test@example.com")
            msg = st.text_area("Message", value="Great news! We found your item. Confidence: 92%. Visit Lost & Found at Terminal 2.")
            if st.form_submit_button("📧  SIMULATE SEND", use_container_width=True):
                database.insert_notification({
                    "case_id": str(uuid4()), "match_id": str(uuid4()),
                    "passenger_email": email, "confidence_score": 0.92,
                    "found_item_description": "Simulated item", "message": msg,
                })
                st.balloons()
                st.rerun()
        return

    for notif in notifications:
        score = notif["confidence_score"]
        emoji = "🟢" if score >= 0.85 else "🟡" if score >= 0.6 else "🔴"
        st.markdown(f"""
        <div class="notif-card">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">
                <div>
                    <span style="font-size:1.2rem">{emoji}</span>
                    <strong style="color:#F0F0F0;margin-left:8px">{notif['passenger_email']}</strong>
                </div>
                <span style="color:#555;font-size:0.8rem">{notif['sent_at'][:19]}</span>
            </div>
            <p style="margin:10px 0;color:#F0F0F0;font-size:0.9rem">{notif.get('message', 'Notification sent.')}</p>
            <p style="color:#555;font-size:0.8rem">Confidence: {score:.0%} · Case: {notif['case_id'][:8]}...</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📤 Send New Notification")
    with st.form("new_notif"):
        email = st.text_input("Email", placeholder="passenger@email.com")
        msg = st.text_area("Message", value="We may have found your lost item! Please visit the airport Lost & Found.")
        if st.form_submit_button("📧  SEND NOTIFICATION", use_container_width=True):
            if email:
                database.insert_notification({
                    "case_id": str(uuid4()), "match_id": str(uuid4()),
                    "passenger_email": email, "confidence_score": 0.85,
                    "found_item_description": "Manual notification", "message": msg,
                })
                st.toast(f"Notification sent to {email}")
                st.rerun()


# ─── Page Router ─────────────────────────────────────────────────────

if "Report Lost" in page:
    page_report_lost_item()
elif "Register Found" in page:
    page_register_found_item()
elif "Match" in page:
    page_check_matches()
elif "Analytics" in page:
    page_analytics()
elif "Notification" in page:
    page_notifications()
