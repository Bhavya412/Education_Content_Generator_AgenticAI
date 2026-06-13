import streamlit as st
import os
import io
import uuid
import base64
from dotenv import load_dotenv

from db.database import (
    init_db,
    log_activity,
    get_recent_activities,
    clear_database,
    create_session,
    get_sessions,
    get_session_details,
    delete_session,
    save_message,
    get_messages,
    update_session_pdf,
    update_session_title
)
from services.pdf_loader import extract_pdf_text
from services.tts_service import text_to_speech
from core.engine import process_user_input

load_dotenv(override=True)
init_db()

TOPIC_THEMES = {
    "physics":       {"bg":"#f0f9ff","g1":"rgba(14,165,233,0.15)","g2":"rgba(99,102,241,0.10)","sidebar":"#0c2340"},
    "chemistry":     {"bg":"#f0fdf4","g1":"rgba(34,197,94,0.14)","g2":"rgba(16,185,129,0.10)","sidebar":"#052e16"},
    "biology":       {"bg":"#fdf4ff","g1":"rgba(168,85,247,0.13)","g2":"rgba(217,70,239,0.08)","sidebar":"#2e1065"},
    "mathematics":   {"bg":"#eff6ff","g1":"rgba(59,130,246,0.14)","g2":"rgba(99,102,241,0.10)","sidebar":"#1e3a8a"},
    "math":          {"bg":"#eff6ff","g1":"rgba(59,130,246,0.14)","g2":"rgba(99,102,241,0.10)","sidebar":"#1e3a8a"},
    "engineering":   {"bg":"#fff7ed","g1":"rgba(249,115,22,0.13)","g2":"rgba(234,179,8,0.09)","sidebar":"#431407"},
    "computer":      {"bg":"#f8fafc","g1":"rgba(99,102,241,0.14)","g2":"rgba(139,92,246,0.10)","sidebar":"#1e1b4b"},
    "programming":   {"bg":"#f8fafc","g1":"rgba(99,102,241,0.14)","g2":"rgba(139,92,246,0.10)","sidebar":"#1e1b4b"},
    "thermodynamics":{"bg":"#fff7ed","g1":"rgba(239,68,68,0.13)","g2":"rgba(249,115,22,0.10)","sidebar":"#450a0a"},
    "astronomy":     {"bg":"#0f0c29","g1":"rgba(99,102,241,0.25)","g2":"rgba(139,92,246,0.18)","sidebar":"#050211"},
    "history":       {"bg":"#fffbeb","g1":"rgba(217,119,6,0.14)","g2":"rgba(180,83,9,0.09)","sidebar":"#451a03"},
    "geography":     {"bg":"#f0fdf4","g1":"rgba(21,128,61,0.13)","g2":"rgba(5,150,105,0.09)","sidebar":"#052e16"},
    "economics":     {"bg":"#fefce8","g1":"rgba(234,179,8,0.14)","g2":"rgba(161,98,7,0.09)","sidebar":"#422006"},
    "psychology":    {"bg":"#fdf2f8","g1":"rgba(236,72,153,0.12)","g2":"rgba(168,85,247,0.09)","sidebar":"#4a044e"},
    "sociology":     {"bg":"#f5f3ff","g1":"rgba(139,92,246,0.13)","g2":"rgba(99,102,241,0.09)","sidebar":"#2e1065"},
    "philosophy":    {"bg":"#f1f5f9","g1":"rgba(71,85,105,0.13)","g2":"rgba(99,102,241,0.09)","sidebar":"#0f172a"},
    "literature":    {"bg":"#fff1f2","g1":"rgba(225,29,72,0.11)","g2":"rgba(249,115,22,0.08)","sidebar":"#4c0519"},
    "language":      {"bg":"#fff1f2","g1":"rgba(225,29,72,0.11)","g2":"rgba(249,115,22,0.08)","sidebar":"#4c0519"},
    "medicine":      {"bg":"#f0fdf4","g1":"rgba(22,163,74,0.13)","g2":"rgba(5,150,105,0.09)","sidebar":"#052e16"},
    "anatomy":       {"bg":"#fff0f0","g1":"rgba(239,68,68,0.13)","g2":"rgba(220,38,38,0.08)","sidebar":"#450a0a"},
    "pharmacology":  {"bg":"#f0f9ff","g1":"rgba(6,182,212,0.13)","g2":"rgba(14,165,233,0.09)","sidebar":"#082f49"},
    "music":         {"bg":"#fdf4ff","g1":"rgba(192,38,211,0.13)","g2":"rgba(168,85,247,0.09)","sidebar":"#3b0764"},
    "art":           {"bg":"#fff7ed","g1":"rgba(249,115,22,0.13)","g2":"rgba(234,179,8,0.09)","sidebar":"#431407"},
    "law":           {"bg":"#f8fafc","g1":"rgba(51,65,85,0.13)","g2":"rgba(71,85,105,0.09)","sidebar":"#0f172a"},
    "business":      {"bg":"#fefce8","g1":"rgba(161,98,7,0.13)","g2":"rgba(234,179,8,0.09)","sidebar":"#422006"},
    "finance":       {"bg":"#fefce8","g1":"rgba(161,98,7,0.13)","g2":"rgba(234,179,8,0.09)","sidebar":"#422006"},
}
DEFAULT_THEME = {"bg":"#f0f4ff","g1":"rgba(99,102,241,0.12)","g2":"rgba(139,92,246,0.10)","sidebar":"#1e1b4b"}

def detect_topic_theme(title: str) -> dict:
    if not title:
        return DEFAULT_THEME
    lower = title.lower()
    for keyword, theme in TOPIC_THEMES.items():
        if keyword in lower:
            return theme
    return DEFAULT_THEME

def get_theme_colors(theme: dict) -> dict:
    bg_color = theme.get("bg", "#f0f4ff")
    is_dark = False
    if bg_color.startswith("#"):
        hex_val = bg_color[1:]
        if len(hex_val) == 6:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            is_dark = luminance < 0.5
    
    if is_dark:
        return {
            "bg": bg_color,
            "g1": theme.get("g1", "rgba(99,102,241,0.25)"),
            "g2": theme.get("g2", "rgba(139,92,246,0.18)"),
            "sidebar": theme.get("sidebar", "#050211"),
            "text": "#e2e8f0",
            "text_inverse": "#1e1b4b",
            "subtext": "#94a3b8",
            "chat_bg_assistant": "#1e1b4b",
            "chat_bg_user": "linear-gradient(135deg, #312e81 0%, #1e1b4b 100%)",
            "input_bg": "#050211",
            "input_text": "#ffffff",
            "uploader_bg": "#050211",
            "card_bg": "#1e1b4b",
            "border": "rgba(165,180,252,0.3)",
            "dark": True
        }
    else:
        return {
            "bg": bg_color,
            "g1": theme.get("g1", "rgba(99,102,241,0.12)"),
            "g2": theme.get("g2", "rgba(139,92,246,0.10)"),
            "sidebar": theme.get("sidebar", "#1e1b4b"),
            "text": "#1e1b4b",
            "text_inverse": "#ffffff",
            "subtext": "#475569",
            "chat_bg_assistant": "#ffffff",
            "chat_bg_user": "linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%)",
            "input_bg": "#ffffff",
            "input_text": "#0f172a",
            "uploader_bg": "#f8f9ff",
            "card_bg": "#ffffff",
            "border": "rgba(99,102,241,0.15)",
            "dark": False
        }

def inject_theme(theme: dict):
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&display=swap');

        :root {{
            --indigo:        #4f46e5;
            --indigo-light:  #6366f1;
            --indigo-dim:    rgba(99,102,241,0.12);
            --indigo-soft:   rgba(99,102,241,0.06);
            --gold:          #d97706;
            --mint:          #059669;
            --text-primary:  {theme['text']};
            --border:        {theme['border']};
            --border-glow:   rgba(99,102,241,0.45);
            --radius-sm:     8px;
            --radius-md:     14px;
        }}

        html, body, .stApp {{
            font-family: 'DM Sans', -apple-system, sans-serif !important;
        }}

        .stApp {{
            min-height: 100vh;
            transition: background 1.2s ease;
            position: relative;
            background: {theme['bg']} !important;
            background-image:
                radial-gradient(ellipse 70% 50% at 10% 0%, {theme['g1']} 0%, transparent 55%),
                radial-gradient(ellipse 60% 45% at 90% 100%, {theme['g2']} 0%, transparent 50%) !important;
        }}
        .stApp::before {{
            content: 'StudyCopilot';
            position: fixed;
            top: 50%; left: 55%;
            transform: translate(-50%, -50%) rotate(-25deg);
            font-family: 'Sora', sans-serif;
            font-size: 13vw;
            font-weight: 900;
            color: rgba(99,102,241,0.045);
            white-space: nowrap;
            pointer-events: none;
            z-index: 0;
            user-select: none;
        }}
        .main .block-container {{ position: relative; z-index: 1; }}
        section[data-testid="stSidebar"] {{ z-index: 2; }}

        /* ── SIDEBAR ── */
        section[data-testid="stSidebar"] {{
            background: {theme['sidebar']} !important;
            border-right: 1px solid rgba(99,102,241,0.2) !important;
            box-shadow: 4px 0 30px rgba(30,27,75,0.3);
        }}
        section[data-testid="stSidebar"] > div {{ padding-top: 0 !important; }}
        section[data-testid="stSidebar"] * {{ color: #e0e7ff !important; }}
        section[data-testid="stSidebar"] .stButton > button {{ color: #c7d2fe !important; }}
        section[data-testid="stSidebar"] .stButton > button:hover {{ color: #ffffff !important; }}

        /* ── LOGO ── */
        .copilot-logo {{
            padding: 1.8rem 1.2rem 1.2rem;
            border-bottom: 1px solid rgba(99,102,241,0.2);
            margin-bottom: 0.5rem;
            position: relative;
            overflow: hidden;
        }}
        .copilot-logo::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(165,180,252,0.8), transparent);
            animation: shimmer 3s ease-in-out infinite;
        }}
        @keyframes shimmer {{ 0%,100% {{ opacity: 0.4; }} 50% {{ opacity: 1; }} }}
        .logo-wordmark {{ font-family: 'Sora', sans-serif; font-size: 1.35rem; font-weight: 800; margin: 0; }}
        .logo-badge {{
            display: inline-flex; align-items: center; gap: 5px; margin-top: 6px;
            background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.3);
            border-radius: 20px; padding: 2px 10px; font-size: 0.68rem; font-weight: 600;
            letter-spacing: 0.08em; text-transform: uppercase;
        }}
        .logo-badge::before {{ content: '●'; font-size: 0.5rem; animation: blink 2s ease-in-out infinite; }}
        @keyframes blink {{ 0%,100%{{ opacity:1; }} 50%{{ opacity:0.3; }} }}
        .sidebar-label {{
            font-family: 'Sora', sans-serif; font-size: 0.65rem; font-weight: 700;
            letter-spacing: 0.12em; text-transform: uppercase;
            color: rgba(199,210,254,0.6) !important; padding: 0.8rem 0 0.4rem; margin: 0;
        }}

        /* ── BUTTONS ── */
        .stButton > button {{
            background: {theme['input_bg']} !important; color: {theme['input_text']} !important;
            border: 1px solid {theme['border']} !important;
            border-radius: var(--radius-sm) !important;
            font-family: 'DM Sans', sans-serif !important; font-weight: 600 !important;
            font-size: 0.83rem !important; padding: 0.45rem 0.9rem !important;
            transition: all 0.2s ease !important;
        }}
        .stButton > button:hover {{
            background: {theme['g1']} !important; border-color: var(--indigo-light) !important;
            color: var(--indigo) !important; transform: translateY(-1px) !important;
        }}
        section[data-testid="stSidebar"] .stButton > button {{
            background: rgba(255,255,255,0.07) !important; color: #c7d2fe !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
        }}
        section[data-testid="stSidebar"] .stButton > button:hover {{
            background: rgba(255,255,255,0.14) !important; color: #ffffff !important;
        }}
        div[data-testid="stSidebar"] .stButton:first-of-type > button {{
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            border-color: transparent !important; color: #ffffff !important;
            font-weight: 700 !important; box-shadow: 0 4px 14px rgba(99,102,241,0.4) !important;
        }}

        /* ── FORM SUBMIT BUTTON ── */
        .stFormSubmitButton > button,
        [data-testid="stFormSubmitButton"] > button {{
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            color: #ffffff !important; font-size: 1rem !important;
            font-weight: 700 !important; border: none !important;
            border-radius: var(--radius-sm) !important;
            box-shadow: 0 4px 14px rgba(99,102,241,0.4) !important;
        }}
        .stFormSubmitButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {{
            background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%) !important;
            color: #ffffff !important;
        }}

        /* ── CHAT INPUT ── */
        div[data-testid="stChatInput"] {{
            background: transparent !important;
        }}
        div[data-testid="stChatInput"] > div {{
            background: {theme['input_bg']} !important;
            border: 1.5px solid {theme['border']} !important;
            border-radius: var(--radius-md) !important;
        }}
        div[data-testid="stChatInput"] > div div,
        div[data-testid="stChatInput"] textarea {{
            background: transparent !important;
            color: {theme['input_text']} !important;
            font-family: 'DM Sans', sans-serif !important;
        }}
        div[data-testid="stChatInput"] textarea::placeholder {{
            color: {theme['subtext']} !important;
        }}
        div[data-testid="stChatInput"] button svg {{
            fill: {theme['input_text']} !important;
        }}

        /* ── CHAT MESSAGES ── */
        [data-testid="stChatMessage"] {{ background: transparent !important; border: none !important; padding: 0.4rem 0 !important; }}
        [data-testid="stChatMessage"][data-role="assistant"] [data-testid="stChatMessageContent"] {{
            background: {theme['chat_bg_assistant']} !important; border: 1px solid {theme['border']} !important;
            border-radius: var(--radius-md) !important; padding: 1.5rem 1.8rem !important;
            box-shadow: 0 2px 12px rgba(99,102,241,0.07) !important; position: relative;
        }}
        [data-testid="stChatMessage"][data-role="assistant"] [data-testid="stChatMessageContent"]::before {{
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, transparent, rgba(99,102,241,0.5), transparent);
            border-radius: var(--radius-md) var(--radius-md) 0 0;
        }}
        [data-testid="stChatMessage"][data-role="user"] [data-testid="stChatMessageContent"] {{
            background: {theme['chat_bg_user']} !important;
            border: 1px solid {theme['border']} !important;
            border-radius: var(--radius-md) !important; padding: 1.2rem 1.8rem !important;
        }}

        /* ── LIGHT BG TEXT — dynamically targets elements with proper color ── */
        .main .block-container p,
        .main .block-container li,
        .main .block-container label,
        .main .block-container span,
        .main .block-container h1,
        .main .block-container h2,
        .main .block-container h3,
        .main .block-container h4,
        .main .block-container h5,
        .main .block-container h6 {{
            color: {theme['text']} !important;
        }}

        [data-testid="stChatMessageContent"] p,
        [data-testid="stChatMessageContent"] span,
        [data-testid="stChatMessageContent"] li,
        [data-testid="stChatMessageContent"] h1,
        [data-testid="stChatMessageContent"] h2,
        [data-testid="stChatMessageContent"] h3,
        [data-testid="stChatMessageContent"] h4,
        [data-testid="stChatMessageContent"] h5,
        [data-testid="stChatMessageContent"] h6 {{
            color: {theme['text']} !important;
        }}

        /* ── SIDEBAR TEXT WHITE ── */
        section[data-testid="stSidebar"] *,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] div {{ color: #c7d2fe !important; }}
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{ color: #e0e7ff !important; }}

        /* ── SESSION HEADER ── */
        .session-header {{
            display: flex; align-items: center; gap: 12px;
            padding: 1.4rem 0 1rem; border-bottom: 1px solid {theme['border']}; margin-bottom: 1.2rem;
        }}
        .session-header-icon {{
            width: 40px; height: 40px; background: var(--indigo-dim);
            border: 1px solid {theme['border']}; border-radius: 10px;
            display: flex; align-items: center; justify-content: center; font-size: 1.1rem;
        }}

        /* ── WELCOME HERO ── */
        .welcome-hero {{ text-align: center; padding: 4rem 2rem 3rem; }}
        .hero-icon {{
            font-size: 3.5rem; display: block; margin-bottom: 1rem;
            animation: float 4s ease-in-out infinite;
        }}
        @keyframes float {{ 0%,100%{{ transform:translateY(0); }} 50%{{ transform:translateY(-8px); }} }}
        .cap-pill {{
            background: var(--indigo-soft); border: 1px solid rgba(99,102,241,0.2);
            border-radius: 30px; padding: 6px 16px; font-size: 0.78rem;
            color: var(--indigo) !important; font-weight: 500; display: inline-block; margin: 4px;
        }}

        /* ── PDF BANNER ── */
        .pdf-banner {{
            display: flex; align-items: center; gap: 12px;
            background: linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(79,70,229,0.04) 100%);
            border: 1px solid {theme['border']}; border-radius: var(--radius-md);
            padding: 0.75rem 1rem; margin-bottom: 0.8rem;
        }}
        .pdf-icon {{
            width: 36px; height: 36px; background: var(--indigo-dim); border-radius: 8px;
            display: flex; align-items: center; justify-content: center; font-size: 1rem; flex-shrink: 0;
        }}

        /* ── FLASHCARD FLIP CARDS ── */
        .fc-scene {{ perspective: 900px; width: 100%; height: 200px; margin-bottom: 1rem; cursor: pointer; }}
        .fc-card {{
            width: 100%; height: 100%; position: relative;
            transform-style: preserve-3d;
            transition: transform 0.55s cubic-bezier(0.4, 0, 0.2, 1); border-radius: 18px;
        }}
        .fc-scene:hover .fc-card, .fc-scene.flipped .fc-card {{ transform: rotateY(180deg); }}
        .fc-face {{
            position: absolute; inset: 0; border-radius: 18px;
            backface-visibility: hidden; -webkit-backface-visibility: hidden;
            display: flex; flex-direction: column;
            justify-content: center; align-items: center;
            padding: 1.4rem 1.6rem; text-align: center; overflow: hidden;
        }}
        .fc-front-face {{ box-shadow: 0 8px 32px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.25); }}
        .fc-front-face.c0 {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .fc-front-face.c1 {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .fc-front-face.c2 {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        .fc-front-face.c3 {{ background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }}
        .fc-front-face.c4 {{ background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }}
        .fc-front-face.c5 {{ background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%); }}
        .fc-front-face.c6 {{ background: linear-gradient(135deg, #fd7043 0%, #ff8a65 100%); }}
        .fc-front-face.c7 {{ background: linear-gradient(135deg, #26c6da 0%, #00acc1 100%); }}
        .fc-back-face {{
            transform: rotateY(180deg);
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%) !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.28); border: 1.5px solid rgba(139,92,246,0.5) !important;
        }}
        .fc-hint {{
            position: absolute; bottom: 12px; right: 16px;
            font-size: 0.6rem; opacity: 0.7; letter-spacing: 0.06em; text-transform: uppercase; font-weight: 600;
        }}
        .fc-icon {{ font-size: 1.6rem; margin-bottom: 8px; opacity: 0.9; }}

        /* ── SCROLLBAR ── */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: rgba(99,102,241,0.2); border-radius: 3px; }}

        /* ── FILE UPLOADER ── */
        [data-testid="stFileUploader"] {{
            background: transparent !important;
            border: none !important;
        }}
        [data-testid="stFileUploaderDropzone"] {{
            background: {theme['uploader_bg']} !important;
            border: 1px dashed {theme['border']} !important;
            border-radius: var(--radius-md) !important;
            padding: 1rem !important;
        }}
        [data-testid="stFileUploaderDropzone"] * {{
            color: {theme['text']} !important;
        }}
        [data-testid="stFileUploaderDropzone"] button {{
            background: {theme['input_bg']} !important;
            color: {theme['input_text']} !important;
            border: 1px solid {theme['border']} !important;
        }}
        [data-testid="stFileUploaderDropzone"] button:hover {{
            background: {theme['g1']} !important;
            color: var(--indigo) !important;
        }}

        /* ── RADIO ── */
        [data-testid="stRadio"] label {{ color: {theme['text']} !important; font-size: 0.85rem !important; }}
        [data-testid="stRadio"] * {{ color: {theme['text']} !important; }}

        /* ── METRICS ── */
        [data-testid="stMetricValue"] {{ color: var(--indigo) !important; }}

        /* ── TOAST ── */
        [data-testid="stToast"] {{ background: {theme['input_bg']} !important; color: {theme['text']} !important; }}

        /* ── SPINNER ── */
        div[data-testid="stSpinner"] p,
        div.stSpinner p,
        div[data-testid="stSpinner"] {{
            color: {theme['text']} !important;
        }}

        hr {{ border: none !important; border-top: 1px solid {theme['border']} !important; margin: 0.8rem 0 !important; }}
        </style>
    """, unsafe_allow_html=True)

st.set_page_config(
    page_title="StudyCopilot — AI Learning Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ── API KEY ──
env_api_key = os.getenv("GROQ_API_KEY")
has_env_key = env_api_key and env_api_key != "gsk_your_groq_api_key_here" and env_api_key.strip() != ""
if "groq_api_key" not in st.session_state:
    st.session_state.groq_api_key = env_api_key if has_env_key else ""
elif has_env_key:
    st.session_state.groq_api_key = env_api_key

# ── SESSION MANAGEMENT ──
# 1. Retrieve or generate user_id
if "user_id" not in st.query_params:
    st.query_params["user_id"] = str(uuid.uuid4())
user_id = st.query_params["user_id"]

# 2. Get sessions for this user
sessions = get_sessions(user_id=user_id)

# 3. Check if tab is freshly opened/refreshed
if "session_initialized" not in st.session_state:
    st.session_state.session_initialized = True
    new_id = str(uuid.uuid4())
    create_session(new_id, "New Chat", user_id=user_id)
    st.session_state.current_session_id = new_id
    sessions = get_sessions(user_id=user_id)

# 4. Fallback if current_session_id is not set or invalid
if "current_session_id" not in st.session_state or not st.session_state.current_session_id:
    if sessions:
        st.session_state.current_session_id = sessions[0]["session_id"]
    else:
        new_id = str(uuid.uuid4())
        create_session(new_id, "New Chat", user_id=user_id)
        st.session_state.current_session_id = new_id
        sessions = get_sessions(user_id=user_id)

current_session = get_session_details(st.session_state.current_session_id)
if not current_session:
    if sessions:
        st.session_state.current_session_id = sessions[0]["session_id"]
        current_session = get_session_details(st.session_state.current_session_id)
    else:
        new_id = str(uuid.uuid4())
        create_session(new_id, "New Chat", user_id=user_id)
        st.session_state.current_session_id = new_id
        current_session = get_session_details(new_id)
        sessions = get_sessions(user_id=user_id)

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("""
        <div class='copilot-logo'>
            <p class='logo-wordmark'>
                <font color="#818cf8">Study</font><font color="#e0e7ff">Copilot</font>
            </p>
            <div class='logo-badge'><font color="#a5b4fc">AI Learning Assistant</font></div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<p class='sidebar-label'>Navigation</p>", unsafe_allow_html=True)

    if st.button("＋  New Chat Session", use_container_width=True):
        new_id = str(uuid.uuid4())
        create_session(new_id, "New Chat", user_id=user_id)
        st.session_state.current_session_id = new_id
        st.session_state.active_audio_index = None
        st.session_state.active_audio_bytes = None
        st.session_state.active_audio_bytes_idx = None
        st.rerun()

    st.markdown("<p class='sidebar-label'>Chat History</p>", unsafe_allow_html=True)

    for s in sessions:
        is_active = s["session_id"] == st.session_state.current_session_id
        col_select, col_del = st.columns([0.85, 0.15])
        btn_label = f"{'▸' if is_active else '○'}  {s['title'][:22]}"
        with col_select:
            if st.button(btn_label, key=f"select_{s['session_id']}", use_container_width=True):
                st.session_state.current_session_id = s["session_id"]
                st.session_state.active_audio_index = None
                st.session_state.active_audio_bytes = None
                st.session_state.active_audio_bytes_idx = None
                st.rerun()
        with col_del:
            if st.button("×", key=f"del_{s['session_id']}", help="Delete session"):
                delete_session(s["session_id"])
                if is_active:
                    st.session_state.current_session_id = None
                st.rerun()

    st.markdown("<p class='sidebar-label'>Settings</p>", unsafe_allow_html=True)
    if not has_env_key:
        st.text_input("Groq API Key", type="password", key="groq_api_key",
                      help="Get a key from console.groq.com", placeholder="gsk_...")

    if st.button("🗑  Clear All History", use_container_width=True):
        clear_database()
        st.session_state.current_session_id = None
        st.session_state.active_audio_index = None
        st.session_state.active_audio_bytes = None
        st.session_state.active_audio_bytes_idx = None
        for k in list(st.session_state.keys()):
            if k.startswith("submitted_"):
                del st.session_state[k]
        st.toast("Entire chat history and database cleared!")
        st.rerun()

# ── APPLY THEME ──
active_title_raw = current_session.get("title") if current_session else "New Chat"
raw_theme = detect_topic_theme(active_title_raw)
topic_theme = get_theme_colors(raw_theme)
inject_theme(topic_theme)

# ── MAIN AREA ──
active_title = active_title_raw
icon = "📚" if active_title.startswith("📚") else "💬"
display_title = active_title.replace("📚 ", "").replace("📁 ", "")
messages = get_messages(st.session_state.current_session_id)
msg_count = len(messages)

st.markdown(f"""
    <div class='session-header'>
        <div class='session-header-icon'>{icon}</div>
        <div>
            <p style='font-family:Sora,sans-serif;font-size:1.35rem;font-weight:800;
                color:{topic_theme["text"]};margin:0;line-height:1.2;'>{display_title}</p>
            <p style='font-size:0.72rem;color:{topic_theme["subtext"]};margin:0;'>
                {msg_count} message{'s' if msg_count != 1 else ''} in this session</p>
        </div>
    </div>
""", unsafe_allow_html=True)

if not messages:
    st.markdown(f"""
        <div class='welcome-hero'>
            <span class='hero-icon'>🎓</span>
            <h1 style='font-family:Sora,sans-serif;font-size:2rem;font-weight:800;
                color:{topic_theme["text"]};margin:0 0 0.5rem;'>Your <span style='color:#6366f1;'>AI Study</span> Partner</h1>
            <p style='color:{topic_theme["subtext"]};font-size:0.95rem;max-width:480px;margin:0 auto 2rem;line-height:1.7;'>
                Upload a PDF to unlock intelligent study tools, or just ask me anything to get started.</p>
            <div>
                <span class='cap-pill'>📝 Practice Quizzes</span>
                <span class='cap-pill'>🎴 Smart Flashcards</span>
                <span class='cap-pill'>📄 Instant Summaries</span>
                <span class='cap-pill'>🔊 Audio Playback</span>
                <span class='cap-pill'>💬 Q&amp;A Chat</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ── RENDER CHAT HISTORY ──
for idx, msg in enumerate(messages):
    with st.chat_message(msg["role"]):

        # ════════════════════════════════════════
        # QUIZ
        # ════════════════════════════════════════
        if msg["type"] == "quiz":
            quiz_data = msg["data"]
            total_q = len(quiz_data)

            st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;
                    background:linear-gradient(135deg,#fef3c7,#fde68a);
                    border:1px solid #f59e0b;border-radius:12px;
                    padding:10px 16px;margin-bottom:14px;">
                    <span style="font-size:1.3rem">📝</span>
                    <div>
                        <font color="#92400e" style="font-family:'Sora',sans-serif;font-size:0.95rem;font-weight:800;display:block;">Practice Quiz</font>
                        <font color="#b45309" style="font-size:0.7rem;display:block;">{total_q} questions · select your answers then submit</font>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            with st.form(key=f"form_{idx}"):
                user_answers = {}
                for q_idx, q in enumerate(quiz_data):
                    st.markdown(f"""
                        <div style="background:{topic_theme['input_bg']};border:1px solid {topic_theme['border']};
                            border-radius:10px;padding:14px 16px 6px;margin-bottom:4px;">
                            <span style="display:inline-block;background:rgba(99,102,241,0.1);
                                border:1px solid rgba(99,102,241,0.25);border-radius:6px;
                                padding:2px 10px;font-size:0.68rem;font-weight:800;
                                color:#4f46e5;letter-spacing:0.06em;margin-bottom:8px;">
                                Q {q_idx+1} of {total_q}
                            </span>
                            <font color="{topic_theme['text']}" style="font-size:0.92rem;font-weight:700;
                                line-height:1.5;display:block;">{q['question']}</font>
                        </div>
                    """, unsafe_allow_html=True)
                    opts = [f"{k}: {v}" for k, v in q['options'].items()]
                    user_answers[q_idx] = st.radio(
                        f"q{q_idx}", opts,
                        key=f"radio_{idx}_{q_idx}",
                        label_visibility="collapsed"
                    )
                    st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

                submitted = st.form_submit_button("✓  Submit Answers", use_container_width=True)

            if submitted or st.session_state.get(f"submitted_{idx}", False):
                st.session_state[f"submitted_{idx}"] = True
                correct_count = 0

                st.markdown("""
                    <div style="background:linear-gradient(135deg,#eff6ff,#dbeafe);
                        border:1px solid #93c5fd;border-radius:10px;
                        padding:10px 16px;margin:10px 0 14px;">
                        <font color="#1e40af" style="font-family:'Sora',sans-serif;
                            font-size:0.88rem;font-weight:800;display:block;">
                            📊 Results &amp; Explanations
                        </font>
                    </div>
                """, unsafe_allow_html=True)

                for q_idx, q in enumerate(quiz_data):
                    selected_letter = user_answers[q_idx].split(":")[0]
                    correct_letter = q['answer']
                    is_correct = selected_letter == correct_letter
                    if is_correct:
                        correct_count += 1
                    bg     = "#f0fdf4" if is_correct else "#fff1f2"
                    border = "#86efac" if is_correct else "#fca5a5"
                    icon_r = "✅" if is_correct else "❌"
                    verdict_text = f"Correct! Your answer: {selected_letter}" if is_correct else f"Your answer: {selected_letter} · Correct: {correct_letter}"
                    verdict_color = "#15803d" if is_correct else "#dc2626"
                    st.markdown(f"""
                        <div style="background:{bg};border:1px solid {border};
                            border-radius:10px;padding:12px 16px;margin-bottom:10px;">
                            <font color="#374151" style="font-size:0.8rem;font-weight:700;display:block;margin-bottom:4px;">
                                {icon_r} Q{q_idx+1}: {q['question']}
                            </font>
                            <font color="{verdict_color}" style="font-size:0.82rem;font-weight:600;display:block;margin-bottom:6px;">
                                {verdict_text}
                            </font>
                            <div style="background:rgba(0,0,0,0.04);border-radius:6px;padding:6px 10px;">
                                <font color="#4b5563" style="font-size:0.78rem;display:block;">
                                    💡 {q['explanation']}
                                </font>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                pct = int(correct_count / total_q * 100)
                score_color = "#4ade80" if pct >= 70 else "#fbbf24" if pct >= 40 else "#f87171"

                # ── FINAL SCORE — uses <font> tags so Streamlit can't override ──
                st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#1e1b4b 0%,#312e81 100%);
                        border-radius:12px;padding:24px;margin-top:12px;text-align:center;
                        border:1px solid rgba(139,92,246,0.4);">
                        <font color="#a5b4fc" style="font-size:0.72rem;font-weight:700;
                            letter-spacing:.12em;text-transform:uppercase;display:block;margin-bottom:8px;">
                            FINAL SCORE
                        </font>
                        <font color="#ffffff" style="font-family:'Sora',sans-serif;font-size:2.8rem;
                            font-weight:800;display:block;line-height:1;">
                            {correct_count}
                            <font color="#a5b4fc" style="font-size:1.2rem;font-weight:500;">
                                &nbsp;/&nbsp;{total_q}
                            </font>
                        </font>
                        <font color="{score_color}" style="font-size:1.1rem;font-weight:700;
                            display:block;margin-top:10px;">
                            {pct}%
                        </font>
                    </div>
                """, unsafe_allow_html=True)

        # ════════════════════════════════════════
        # FLASHCARDS
        # ════════════════════════════════════════
        elif msg["type"] == "flashcards":
            cards_data = msg["data"]
            total = len(cards_data)
            st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                    <div style="width:36px;height:36px;background:rgba(217,119,6,0.1);
                        border:1px solid rgba(245,200,66,0.3);border-radius:8px;
                        display:flex;align-items:center;justify-content:center;font-size:1rem;">🎴</div>
                    <font color="{topic_theme['text']}" style="font-family:'Sora',sans-serif;font-size:1rem;font-weight:700;">
                        Flashcards
                        <font color="{topic_theme['subtext']}" style="font-size:0.72rem;font-weight:500;">
                            ({total} cards · hover to flip)
                        </font>
                    </font>
                </div>
            """, unsafe_allow_html=True)

            color_classes = ["c0","c1","c2","c3","c4","c5","c6","c7"]
            topic_icons   = ["💡","🔬","📐","🧠","⚡","🌿","🔭","🎯","📊","🧬","🏛️","🎨"]
            cards_html = "<div style='display:grid;grid-template-columns:1fr 1fr;gap:14px;'>"
            for c_idx, card in enumerate(cards_data):
                cc = color_classes[c_idx % len(color_classes)]
                ic = topic_icons[c_idx % len(topic_icons)]
                front_text = card["front"].replace("'","&#39;").replace('"',"&quot;")
                back_text  = card["back"].replace("'","&#39;").replace('"',"&quot;")
                cards_html += f"""
                <div class='fc-scene' onclick='this.classList.toggle("flipped")'>
                    <div class='fc-card'>
                        <div class='fc-face fc-front-face {cc}'>
                            <div class='fc-icon'>{ic}</div>
                            <div style='display:inline-flex;align-items:center;gap:5px;
                                background:rgba(255,255,255,0.25);border:1px solid rgba(255,255,255,0.4);
                                border-radius:20px;padding:3px 12px;margin-bottom:10px;'>
                                <font color="#ffffff" style="font-size:0.62rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;">❓ Card {c_idx+1}</font>
                            </div>
                            <font color="#ffffff" style="font-family:'Sora',sans-serif;font-size:0.92rem;
                                font-weight:700;line-height:1.45;display:block;text-align:center;">{front_text}</font>
                            <font color="rgba(255,255,255,0.8)" style="position:absolute;bottom:12px;right:16px;
                                font-size:0.6rem;text-transform:uppercase;letter-spacing:0.06em;">hover to flip →</font>
                        </div>
                        <div class='fc-face fc-back-face'>
                            <div style='display:inline-flex;align-items:center;gap:5px;
                                background:rgba(139,92,246,0.35);border:1px solid rgba(167,139,250,0.6);
                                border-radius:20px;padding:3px 12px;margin-bottom:10px;'>
                                <font color="#e9d5ff" style="font-size:0.62rem;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;">💡 Answer</font>
                            </div>
                            <font color="#e0e7ff" style="font-family:'DM Sans',sans-serif;font-size:0.86rem;
                                font-weight:500;line-height:1.65;display:block;text-align:center;">{back_text}</font>
                            <font color="rgba(167,139,250,0.8)" style="position:absolute;bottom:12px;right:16px;
                                font-size:0.6rem;text-transform:uppercase;letter-spacing:0.06em;">← flip back</font>
                        </div>
                    </div>
                </div>"""
            cards_html += "</div>"
            st.markdown(cards_html, unsafe_allow_html=True)

        # ════════════════════════════════════════
        # SUMMARY
        # ════════════════════════════════════════
        elif msg["type"] == "summary":
            import re as mdre
            raw = msg["content"]

            # ── Dark header — <font> tags so Streamlit can't recolor them ──
            st.markdown(
                "<div style='background:linear-gradient(135deg,#1e1b4b 0%,#312e81 60%,#4f46e5 100%);"
                "border-radius:14px 14px 0 0;padding:14px 20px;"
                "display:flex;align-items:center;gap:12px;'>"
                "<div style='width:38px;height:38px;background:rgba(255,255,255,0.15);"
                "border-radius:10px;display:flex;align-items:center;"
                "justify-content:center;font-size:1.1rem;flex-shrink:0;'>📄</div>"
                "<div>"
                "<font color='#ffffff' style='font-family:Sora,sans-serif;font-size:1rem;"
                "font-weight:800;display:block;'>Study Summary</font>"
                "<font color='#a5b4fc' style='font-size:0.68rem;font-weight:500;display:block;'>"
                "AI-generated from your document</font>"
                "</div></div>"
                f"<div style='background:{topic_theme['input_bg']};border:1px solid {topic_theme['border']};"
                "border-top:none;border-radius:0 0 14px 14px;padding:20px 22px 16px;'>",
                unsafe_allow_html=True
            )

            lines_md = raw.split("\n")
            html_parts = []
            in_ul = False
            for line in lines_md:
                s = line.strip()
                if not s:
                    if in_ul: html_parts.append("</ul>"); in_ul = False
                    html_parts.append("<div style='margin:6px 0'></div>")
                    continue
                def bold(t):
                    t = mdre.sub(r'\*\*(.+?)\*\*', f'<strong style="color:{topic_theme["text"]};font-weight:700;">\\1</strong>', t)
                    t = mdre.sub(r'\*(.+?)\*',     r'<em style="color:#6366f1;">\1</em>', t)
                    return t
                if s.startswith("### "):
                    if in_ul: html_parts.append("</ul>"); in_ul = False
                    html_parts.append(f"<font color='#6366f1' style='font-family:Sora,sans-serif;font-size:0.9rem;font-weight:700;display:block;margin:12px 0 4px;'>{bold(s[4:])}</font>")
                elif s.startswith("## "):
                    if in_ul: html_parts.append("</ul>"); in_ul = False
                    html_parts.append(f"<font color='{topic_theme['text']}' style='font-family:Sora,sans-serif;font-size:1rem;font-weight:800;display:block;margin:14px 0 5px;border-bottom:2px solid rgba(99,102,241,0.2);padding-bottom:6px;'>{bold(s[3:])}</font>")
                elif s.startswith("# "):
                    if in_ul: html_parts.append("</ul>"); in_ul = False
                    html_parts.append(f"<font color='{topic_theme['text']}' style='font-family:Sora,sans-serif;font-size:1.15rem;font-weight:800;display:block;margin:16px 0 6px;'>{bold(s[2:])}</font>")
                elif s.startswith("- ") or s.startswith("* "):
                    if not in_ul:
                        html_parts.append("<ul style='padding-left:0;margin:8px 0;list-style:none;'>")
                        in_ul = True
                    html_parts.append(
                        "<li style='display:flex;gap:8px;align-items:flex-start;padding:5px 0;'>"
                        "<span style='flex-shrink:0;margin-top:6px;width:7px;height:7px;border-radius:50%;"
                        "background:linear-gradient(135deg,#6366f1,#a855f7);display:inline-block;'></span>"
                        f"<font color='{topic_theme['text']}' style='font-size:0.86rem;line-height:1.6;'>{bold(s[2:])}</font></li>"
                    )
                else:
                    if in_ul: html_parts.append("</ul>"); in_ul = False
                    html_parts.append(f"<font color='{topic_theme['text']}' style='font-size:0.88rem;line-height:1.75;display:block;margin:4px 0;'>{bold(s)}</font>")
            if in_ul:
                html_parts.append("</ul>")

            st.markdown("\n".join(html_parts) + "\n</div>", unsafe_allow_html=True)

        # ════════════════════════════════════════
        # AUDIO
        # ════════════════════════════════════════
        elif msg["type"] == "audio":
            st.markdown(msg["content"])
            audio_bytes = base64.b64decode(msg["msg_data"].encode('utf-8'))
            st.audio(io.BytesIO(audio_bytes), format="audio/mp3")

        # ════════════════════════════════════════
        # REGULAR CHAT
        # ════════════════════════════════════════
        else:
            st.markdown(msg["content"])

        # ── Read-aloud ──
        if msg["role"] == "assistant" and msg["type"] in ["chat", "summary"]:
            st.write("")
            if st.session_state.get("active_audio_index") == idx:
                if "active_audio_bytes" not in st.session_state or st.session_state.get("active_audio_bytes_idx") != idx:
                    with st.spinner("Generating audio…"):
                        audio_buffer = text_to_speech(msg["content"])
                        st.session_state.active_audio_bytes = audio_buffer.read()
                        st.session_state.active_audio_bytes_idx = idx
                st.audio(st.session_state.active_audio_bytes, format="audio/mp3")
                if st.button("⏹ Stop", key=f"stop_{idx}"):
                    st.session_state.active_audio_index = None
                    st.session_state.active_audio_bytes = None
                    st.session_state.active_audio_bytes_idx = None
                    st.rerun()
            else:
                if st.button("🔊 Read Aloud", key=f"listen_{idx}"):
                    st.session_state.active_audio_index = idx
                    st.rerun()

# ── BOTTOM: PDF + CHAT INPUT ──
st.markdown("---")

pdf_name = current_session.get("pdf_name")
pdf_text = current_session.get("pdf_text")
pdf_hash = current_session.get("pdf_hash")

if pdf_name:
    word_count = len(pdf_text.split()) if pdf_text else 0
    col_banner, col_remove = st.columns([0.82, 0.18])
    with col_banner:
        st.markdown(f"""
            <div class='pdf-banner'>
                <div class='pdf-icon'>📄</div>
                <div style='flex:1;min-width:0;'>
                    <font color="{topic_theme['text']}" style="font-weight:600;font-size:0.85rem;display:block;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{pdf_name}</font>
                    <font color="{topic_theme['subtext']}" style="font-size:0.72rem;display:block;margin-top:1px;">
                        {word_count:,} words extracted · Ready for study tools</font>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_remove:
        if st.button("Remove", use_container_width=True):
            update_session_pdf(st.session_state.current_session_id, None, None, None)
            st.toast("PDF removed from session.")
            st.rerun()
else:
    uploaded_file = st.file_uploader(
        "Upload a PDF to unlock study tools", type="pdf", key="pdf_uploader",
        help="Upload study materials to ask questions, create quizzes, flashcards, or summaries."
    )
    if uploaded_file:
        with st.spinner("Extracting study content…"):
            try:
                text, file_hash = extract_pdf_text(uploaded_file)
                if not text.strip():
                    st.error("⚠️ The PDF contains no extractable text. It might be scanned or image-only.")
                else:
                    update_session_pdf(st.session_state.current_session_id, uploaded_file.name, text, file_hash)
                    update_session_title(st.session_state.current_session_id, f"📚 {uploaded_file.name}")
                    st.toast("PDF uploaded and parsed successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error parsing PDF: {e}")

# ── QUICK ACTION CHIPS ──
if pdf_name:
    cols_actions = st.columns(4)
    with cols_actions[0]:
        if st.button("📝  Quiz Me", use_container_width=True):
            st.session_state.prompt_injection = "generate quiz"
    with cols_actions[1]:
        if st.button("🎴  Flashcards", use_container_width=True):
            st.session_state.prompt_injection = "create flashcards"
    with cols_actions[2]:
        if st.button("📄  Summarize", use_container_width=True):
            st.session_state.prompt_injection = "summarize content"
    with cols_actions[3]:
        if st.button("🔊  Audio Summary", use_container_width=True):
            st.session_state.prompt_injection = "generate audio"

# ── CHAT INPUT ──
user_query = st.chat_input("Ask a question about your study material or type a command...")

if "prompt_injection" in st.session_state and st.session_state.prompt_injection:
    user_query = st.session_state.prompt_injection
    del st.session_state.prompt_injection

if user_query:
    save_message(st.session_state.current_session_id, "user", user_query, "chat")

    if active_title == "New Chat":
        short_title = user_query[:35] + "..." if len(user_query) > 35 else user_query
        update_session_title(st.session_state.current_session_id, short_title)

    if not st.session_state.groq_api_key:
        save_message(
            st.session_state.current_session_id, "assistant",
            "⚠️ Groq API Key is missing. Please configure GROQ_API_KEY in your `.env` file or enter it in the sidebar.",
            "chat"
        )
        st.rerun()
    else:
        with st.spinner("Thinking..."):
            res_dict = process_user_input(
                query=user_query,
                pdf_text=pdf_text,
                pdf_hash=pdf_hash,
                chat_history=get_messages(st.session_state.current_session_id),
                api_key=st.session_state.groq_api_key
            )
            intent   = res_dict["intent"]
            response = res_dict["response"]

            if intent == "quiz":
                save_message(st.session_state.current_session_id, "assistant", "Interactive Quiz", "quiz", response)
            elif intent == "flashcard":
                save_message(st.session_state.current_session_id, "assistant", "Concept Flashcards", "flashcards", response)
            elif intent == "summary":
                save_message(st.session_state.current_session_id, "assistant", response, "summary")
            elif intent == "audio":
                audio_buffer = res_dict["audio_data"]
                audio_base64 = base64.b64encode(audio_buffer.read()).decode('utf-8')
                save_message(st.session_state.current_session_id, "assistant", response, "audio", audio_base64)
            else:
                save_message(st.session_state.current_session_id, "assistant", response, "chat")

            st.rerun()
