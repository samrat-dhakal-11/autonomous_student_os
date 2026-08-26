import streamlit as st
import json, hashlib, os, re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path as Pt

# ── Load .env from parent folders ───────────────────────────────────────
for p in [Pt.cwd()] + list(Pt.cwd().parents[:5]):
    candidate = p / ".env"
    if candidate.exists():
        load_dotenv(dotenv_path=candidate)
        break
else:
    load_dotenv()

# ── Imports from your existing agents ──────────────────────────────────
try:
    from agents.master_router import run_master_router
    from agents.productivity import analyze_files, organize_files
    from agents.academics import run_academics_agent, list_academic_pdfs
    from agents.finance import run_finance_agent
    from agents.career import run_career_agent
except Exception as e:
    st.error(f"Agent import error: {e}")
    run_master_router = run_academics_agent = run_finance_agent = run_career_agent = None
    analyze_files = organize_files = list_academic_pdfs = None

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Student OS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth helpers ───────────────────────────────────────────────────────
USERS_FILE = Path("data/users.json")
CHATS_DIR  = Path("data/chats")
USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
CHATS_DIR.mkdir(parents=True, exist_ok=True)

def load_users():
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    return {}

def save_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=2))

def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

def load_user_chats(email):
    f = CHATS_DIR / f"{email}.json"
    if f.exists():
        return json.loads(f.read_text())
    return []

def save_user_chats(email, chats):
    (CHATS_DIR / f"{email}.json").write_text(json.dumps(chats, indent=2))

# ── Session state ──────────────────────────────────────────────────────
def init_state():
    defaults = {
        "authenticated": False,
        "user": None,
        "auth_mode": "signin",
        "current_view": "chat",
        "chat_history": [],
        "chats": [],
        "active_chat_id": None,
        "productivity_logs": [],
        "finance_data": None,
        "career_session": {"role": "Software Engineer", "topic": "technical", "history": [], "current_question": ""},
        "sidebar_collapsed": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── CSS Injection ──────────────────────────────────────────────────────
CSS = """
<style>
/* ── Import Google Font ─────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

* {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── GLOBAL DARK THEME ─────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background: #080b1a !important;
    color: #e8e8f0 !important;
}
[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse at 20% 50%, rgba(30, 27, 75, 0.4) 0%, #080b1a 70%) !important;
}
header[data-testid="stHeader"] { display: none !important; }

/* ── SCROLLBAR ─────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); border-radius: 10px; }
::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #6366f1, #a78bfa); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #818cf8; }

/* ── SIDEBAR ───────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(10, 14, 30, 0.85) !important;
    backdrop-filter: blur(24px) !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    padding-top: 20px !important;
}
[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    color: rgba(255,255,255,0.65) !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    padding: 8px 12px !important;
    text-align: left !important;
    justify-content: flex-start !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.04) !important;
    color: #ffffff !important;
    border-color: rgba(255,255,255,0.12) !important;
    transform: translateX(4px);
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 16px rgba(99,102,241,0.25) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 28px rgba(99,102,241,0.4) !important;
    transform: translateY(-2px) scale(1.02) !important;
}

/* Sidebar header logo */
.sidebar-logo {
    display: flex; align-items: center; gap: 12px; padding: 0 12px 20px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 16px;
}
.sidebar-logo-icon {
    width: 40px; height: 40px; border-radius: 14px;
    background: linear-gradient(135deg, #6366f1, #a78bfa);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; box-shadow: 0 4px 16px rgba(99,102,241,0.3);
}
.sidebar-logo-text {
    color: white; font-weight: 700; font-size: 1.2rem; letter-spacing: -0.02em;
}
.sidebar-logo-sub {
    color: rgba(255,255,255,0.3); font-size: 0.65rem; text-transform: uppercase;
    letter-spacing: 0.15em; font-weight: 500;
}

/* ── INPUTS ────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stChatInput > div > div > input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    caret-color: #a78bfa !important;
    font-size: 0.95rem !important;
    padding: 10px 14px !important;
    transition: border 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(99,102,241,0.5) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.08) !important;
}
.stTextInput > label,
.stTextArea > label,
.stSelectbox > label,
.stFileUploader > label {
    color: rgba(255,255,255,0.4) !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}

/* ── BUTTONS ───────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
    font-size: 0.9rem !important;
    padding: 8px 16px !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 32px rgba(99,102,241,0.4) !important;
    transform: translateY(-2px) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: rgba(255,255,255,0.7) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.15) !important;
    color: white !important;
}

/* ── CARDS / CONTAINERS ───────────────────────────────────────────── */
.glass-card {
    background: rgba(255,255,255,0.02) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 20px !important;
    padding: 24px !important;
    transition: all 0.25s ease !important;
}
.glass-card:hover {
    border-color: rgba(255,255,255,0.12) !important;
    box-shadow: 0 12px 40px rgba(0,0,0,0.3) !important;
}

/* ── METRICS ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 16px !important;
    padding: 18px 16px !important;
    transition: all 0.2s !important;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(99,102,241,0.2) !important;
    background: rgba(255,255,255,0.04) !important;
}
[data-testid="stMetric"] label {
    color: rgba(255,255,255,0.4) !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-weight: 600 !important;
}
[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: white !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

/* ── TABS ──────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 14px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
}
.stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.4) !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    border: none !important;
    font-size: 0.85rem !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border-radius: 10px !important;
}
.stTabs [aria-selected="true"] {
    color: white !important;
}

/* ── CHAT MESSAGES ─────────────────────────────────────────────────── */
.stChatMessage {
    background: transparent !important;
}
.stChatMessage [data-testid="stChatMessageContent"] {
    background: rgba(20, 25, 55, 0.7) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 18px !important;
    padding: 16px 20px !important;
    color: rgba(255,255,255,0.85) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2) !important;
}
.stChatMessage [data-testid="stChatMessageAvatarIcon"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border-radius: 50% !important;
}

/* User message right alignment */
.stChatMessage[data-testid="stChatMessage"]:nth-of-type(odd) [data-testid="stChatMessageContent"] {
    background: rgba(99,102,241,0.15) !important;
    border: 1px solid rgba(99,102,241,0.2) !important;
}

/* ── CHAT INPUT ───────────────────────────────────────────────────── */
[data-testid="stChatInput"] {
    background: rgba(20, 25, 55, 0.7) !important;
    backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 16px !important;
    padding: 4px 8px !important;
    box-shadow: 0 4px 30px rgba(0,0,0,0.3) !important;
}
[data-testid="stChatInput"] input {
    background: transparent !important;
    border: none !important;
    color: white !important;
    font-size: 0.95rem !important;
    padding: 8px 12px !important;
}
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border-radius: 50% !important;
    width: 40px !important;
    height: 40px !important;
    box-shadow: 0 4px 16px rgba(99,102,241,0.3) !important;
    margin: 4px !important;
}
[data-testid="stChatInput"] button:hover {
    transform: scale(1.05) !important;
}

/* ── SELECTBOX ────────────────────────────────────────────────────── */
.stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    color: white !important;
}
.stSelectbox svg { color: rgba(255,255,255,0.4) !important; }

/* ── FILE UPLOADER ─────────────────────────────────────────────────── */
.stFileUploader > div > div {
    background: rgba(255,255,255,0.02) !important;
    border: 2px dashed rgba(255,255,255,0.1) !important;
    border-radius: 16px !important;
    color: rgba(255,255,255,0.4) !important;
    transition: all 0.2s !important;
}
.stFileUploader > div > div:hover {
    border-color: rgba(99,102,241,0.4) !important;
    background: rgba(99,102,241,0.04) !important;
}

/* ── TABLES ────────────────────────────────────────────────────────── */
.stMarkdown table {
    background: rgba(255,255,255,0.02) !important;
    border-collapse: separate !important;
    border-spacing: 0 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
}
.stMarkdown th {
    background: rgba(255,255,255,0.04) !important;
    color: rgba(255,255,255,0.7) !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.05em !important;
    padding: 12px 16px !important;
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
}
.stMarkdown td {
    padding: 10px 16px !important;
    border-bottom: 1px solid rgba(255,255,255,0.04) !important;
    color: rgba(255,255,255,0.8) !important;
}
.stMarkdown tr:last-child td { border-bottom: none !important; }

/* ── ALERTS ────────────────────────────────────────────────────────── */
.stAlert {
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    background: rgba(255,255,255,0.02) !important;
    backdrop-filter: blur(8px) !important;
}

/* ── LOGIN PAGE ────────────────────────────────────────────────────── */
.login-bg {
    position: fixed; top:0; left:0; width:100vw; height:100vh;
    background: #080b1a; z-index: -1; overflow: hidden;
}
.orb {
    position: absolute; border-radius: 50%; filter: blur(140px);
    animation: float 16s ease-in-out infinite;
}
.orb1 { width: 600px; height: 600px; background: rgba(99,102,241,0.12); top: -200px; left: -200px; animation-delay: 0s; }
.orb2 { width: 700px; height: 700px; background: rgba(139,92,246,0.10); bottom: -250px; right: -250px; animation-delay: -5s; }
.orb3 { width: 400px; height: 400px; background: rgba(236,72,153,0.06); top: 30%; right: 10%; animation-delay: -10s; }
@keyframes float {
    0%,100% { transform: translate(0,0) scale(1); }
    33% { transform: translate(40px,-40px) scale(1.05); }
    66% { transform: translate(-30px,30px) scale(0.95); }
}
.login-card {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(40px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 28px;
    padding: 48px 40px;
    max-width: 400px;
    margin: 0 auto;
    box-shadow: 0 30px 80px rgba(0,0,0,0.6);
    transition: all 0.3s;
}
.login-card:hover {
    border-color: rgba(255,255,255,0.1);
}
.login-logo {
    width: 64px; height: 64px; border-radius: 20px;
    background: linear-gradient(135deg, #6366f1, #a78bfa);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 16px;
    font-size: 30px;
    box-shadow: 0 8px 30px rgba(99,102,241,0.3);
}
.login-title { text-align: center; color: white; font-size: 26px; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 4px; }
.login-subtitle { text-align: center; color: rgba(255,255,255,0.35); font-size: 14px; margin-bottom: 28px; }
.tab-row { display: flex; background: rgba(255,255,255,0.04); border-radius: 14px; padding: 4px; margin-bottom: 24px; border: 1px solid rgba(255,255,255,0.06); }
.tab-btn { flex: 1; padding: 10px; text-align: center; border-radius: 10px; cursor: default; font-size: 14px; font-weight: 500; transition: all 0.3s; border: none; background: transparent; color: rgba(255,255,255,0.5); }
.tab-btn.active { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; box-shadow: 0 4px 20px rgba(99,102,241,0.25); }
.input-label { font-size: 11px; color: rgba(255,255,255,0.35); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; margin-left: 4px; font-weight: 600; }
.footer-text { text-align: center; font-size: 11px; color: rgba(255,255,255,0.2); margin-top: 20px; }

/* ── MISCELLANEOUS ────────────────────────────────────────────────── */
.stExpander {
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 16px !important;
    background: rgba(255,255,255,0.02) !important;
}
.stExpander > div:first-child {
    background: rgba(255,255,255,0.02) !important;
    border-radius: 16px !important;
}
hr {
    border-color: rgba(255,255,255,0.05) !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ── Helper to render glass cards ──────────────────────────────────────
def glass_container(content_func):
    """Decorator-like helper to wrap content in a glass card."""
    # We'll just use inline markdown in each section
    pass

# ═══════════════════════════════════════════════════════════════════════
# LOGIN / REGISTER PAGE
# ═══════════════════════════════════════════════════════════════════════
def show_login_page():
    # Background orbs (pure CSS)
    st.markdown("""
    <div class="login-bg">
        <div class="orb orb1"></div>
        <div class="orb orb2"></div>
        <div class="orb orb3"></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2.2, 1])
    with col2:
        st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div class="login-card">
            <div class="login-logo">🎓</div>
            <div class="login-title">Student OS</div>
            <div class="login-subtitle">Autonomous Agent System</div>
        </div>
        """, unsafe_allow_html=True)

        mode = st.session_state.auth_mode
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sign In", use_container_width=True,
                         type="primary" if mode=="signin" else "secondary", key="tab_signin"):
                st.session_state.auth_mode = "signin"
                st.rerun()
        with c2:
            if st.button("Create Account", use_container_width=True,
                         type="primary" if mode=="signup" else "secondary", key="tab_signup"):
                st.session_state.auth_mode = "signup"
                st.rerun()

        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

        if mode == "signup":
            name = st.text_input("Full Name", placeholder="John Doe", key="reg_name")
        email = st.text_input("Email", placeholder="you@example.com", key="auth_email")
        pw = st.text_input("Password", type="password", placeholder="••••••••", key="auth_pw")
        if mode == "signup":
            pw2 = st.text_input("Confirm Password", type="password", placeholder="••••••••", key="auth_pw2")

        btn_label = "Sign In" if mode == "signin" else "Create Account"
        if st.button(btn_label, use_container_width=True, type="primary", key="auth_submit"):
            users = load_users()
            if mode == "signin":
                if email in users and users[email]["password"] == hash_pw(pw):
                    st.session_state.authenticated = True
                    st.session_state.user = {"email": email, "name": users[email].get("name", email.split("@")[0])}
                    st.session_state.chats = load_user_chats(email)
                    st.rerun()
                else:
                    st.error("Invalid email or password")
            else:
                if email in users:
                    st.error("Account already exists")
                elif pw != pw2:
                    st.error("Passwords do not match")
                elif len(pw) < 4:
                    st.error("Password too short")
                else:
                    users[email] = {"password": hash_pw(pw), "name": name or email.split("@")[0]}
                    save_users(users)
                    st.session_state.authenticated = True
                    st.session_state.user = {"email": email, "name": name or email.split("@")[0]}
                    st.session_state.chats = []
                    st.success("Account created! Welcome.")
                    st.rerun()

        st.markdown("""
        <div style="margin-top:24px; text-align:center; font-size:12px; color:rgba(255,255,255,0.2);">
            Secure local auth · Data stored locally
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════
def render_sidebar():
    user = st.session_state.user
    chats = st.session_state.chats

    with st.sidebar:
        # Logo
        st.markdown("""
        <div class="sidebar-logo">
            <div class="sidebar-logo-icon">🎓</div>
            <div>
                <div class="sidebar-logo-text">Student OS</div>
                <div class="sidebar-logo-sub">Autonomous Agent</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # New Chat
        if st.button("➕ New Chat", use_container_width=True, key="new_chat_btn"):
            new_id = datetime.now().strftime("%Y%m%d%H%M%S")
            new_chat = {"id": new_id, "title": "New conversation", "pinned": False, "messages": []}
            st.session_state.chats.insert(0, new_chat)
            st.session_state.active_chat_id = new_id
            st.session_state.chat_history = []
            st.session_state.current_view = "chat"
            save_user_chats(user["email"], st.session_state.chats)
            st.rerun()

        st.markdown("<div style='margin:12px 0;height:1px;background:rgba(255,255,255,0.05);'></div>", unsafe_allow_html=True)

        # Chat History
        st.markdown("<div style='font-size:0.65rem;color:rgba(255,255,255,0.25);text-transform:uppercase;letter-spacing:0.15em;font-weight:600;margin-bottom:8px;padding-left:4px;'>Chat History</div>", unsafe_allow_html=True)

        sorted_chats = sorted(chats, key=lambda x: (not x.get("pinned", False), x.get("title", "")))

        for chat in sorted_chats:
            is_active = chat["id"] == st.session_state.active_chat_id
            pin_icon = "📌" if chat.get("pinned") else "💬"
            active_style = "background:linear-gradient(90deg,rgba(99,102,241,0.15),rgba(139,92,246,0.10));border:1px solid rgba(99,102,241,0.2);color:white;" if is_active else "background:transparent;border:1px solid transparent;color:rgba(255,255,255,0.5);"

            cols = st.columns([6, 1])
            with cols[0]:
                if st.button(f"{pin_icon} {chat['title']}", key=f"chat_{chat['id']}", use_container_width=True):
                    st.session_state.active_chat_id = chat["id"]
                    st.session_state.chat_history = chat.get("messages", [])
                    st.session_state.current_view = "chat"
                    st.rerun()
            with cols[1]:
                with st.popover("⋮", use_container_width=True):
                    st.markdown(f"**{chat['title'][:30]}**")
                    if st.button("📌 Pin" if not chat.get("pinned") else "📌 Unpin", key=f"pin_{chat['id']}"):
                        chat["pinned"] = not chat.get("pinned", False)
                        save_user_chats(user["email"], st.session_state.chats)
                        st.rerun()
                    if st.button("✏️ Rename", key=f"ren_{chat['id']}"):
                        st.session_state[f"renaming_{chat['id']}"] = True
                        st.rerun()
                    if st.button("🗑️ Delete", key=f"del_{chat['id']}"):
                        st.session_state.chats = [c for c in st.session_state.chats if c["id"] != chat["id"]]
                        if st.session_state.active_chat_id == chat["id"]:
                            st.session_state.active_chat_id = None
                            st.session_state.chat_history = []
                        save_user_chats(user["email"], st.session_state.chats)
                        st.rerun()

        # Handle rename inline
        for chat in sorted_chats:
            if st.session_state.get(f"renaming_{chat['id']}", False):
                new_title = st.text_input("Rename", value=chat["title"], key=f"rename_inp_{chat['id']}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Save", key=f"save_{chat['id']}"):
                        chat["title"] = new_title
                        save_user_chats(user["email"], st.session_state.chats)
                        del st.session_state[f"renaming_{chat['id']}"]
                        st.rerun()
                with c2:
                    if st.button("Cancel", key=f"cancel_{chat['id']}"):
                        del st.session_state[f"renaming_{chat['id']}"]
                        st.rerun()

        st.markdown("<div style='margin:16px 0;height:1px;background:rgba(255,255,255,0.05);'></div>", unsafe_allow_html=True)

        # Agents
        st.markdown("<div style='font-size:0.65rem;color:rgba(255,255,255,0.25);text-transform:uppercase;letter-spacing:0.15em;font-weight:600;margin-bottom:8px;padding-left:4px;'>Agents</div>", unsafe_allow_html=True)

        agents = [
            ("💬", "Chat", "chat"),
            ("🗂️", "Productivity", "productivity"),
            ("📚", "Academics", "academics"),
            ("💰", "Finance", "finance"),
            ("🎯", "Career", "career"),
        ]
        for icon, label, key in agents:
            is_active = st.session_state.current_view == key
            if st.button(f"{icon} {label}", key=f"agent_{key}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.current_view = key
                st.rerun()

        # Spacer
        st.markdown("<div style='flex:1;min-height:40px;'></div>", unsafe_allow_html=True)

        # User profile
        st.markdown("<div style='margin:12px 0;height:1px;background:rgba(255,255,255,0.05);'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:14px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);">
            <div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#818cf8,#c084fc);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:14px;flex-shrink:0;">{user['name'][0].upper()}</div>
            <div style="flex:1;min-width:0;">
                <div style="color:white;font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{user['name']}</div>
                <div style="color:rgba(255,255,255,0.3);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{user['email']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.chats = []
            st.session_state.active_chat_id = None
            st.session_state.chat_history = []
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# CHAT VIEW
# ═══════════════════════════════════════════════════════════════════════
def show_chat_view():
    user = st.session_state.user
    chats = st.session_state.chats
    chat_history = st.session_state.chat_history

    def save_current_chat():
        for c in chats:
            if c["id"] == st.session_state.active_chat_id:
                c["messages"] = chat_history
                if chat_history and len(chat_history) > 0:
                    first_user = next((m["content"] for m in chat_history if m["role"] == "user"), "Conversation")
                    c["title"] = first_user[:40] if len(first_user) <= 40 else first_user[:37] + "..."
                save_user_chats(user["email"], chats)
                break

    if not chat_history:
        # Landing page
        st.markdown("""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:55vh;text-align:center;padding:20px;">
            <div style="width:72px;height:72px;border-radius:28px;background:linear-gradient(135deg,rgba(99,102,241,0.15),rgba(139,92,246,0.10));display:flex;align-items:center;justify-content:center;margin-bottom:24px;font-size:34px;backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.05);">🧠</div>
            <h1 style="font-size:32px;font-weight:700;background:linear-gradient(135deg,#a5b4fc,#c4b5fd);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:12px;">What can I help with?</h1>
            <p style="color:rgba(255,255,255,0.4);font-size:15px;max-width:480px;line-height:1.6;margin-bottom:32px;">
                I am the Master Router. I can help you organize files, debug code, analyze bank statements, or prepare for interviews.
            </p>
            <div style="display:flex;flex-wrap:wrap;gap:12px;justify-content:center;">
                <span class="suggestion-chip" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:30px;padding:8px 18px;color:rgba(255,255,255,0.7);font-size:14px;cursor:default;">📁 Organize my downloads</span>
                <span class="suggestion-chip" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:30px;padding:8px 18px;color:rgba(255,255,255,0.7);font-size:14px;cursor:default;">💻 Debug my Python code</span>
                <span class="suggestion-chip" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:30px;padding:8px 18px;color:rgba(255,255,255,0.7);font-size:14px;cursor:default;">💰 Analyze my spending</span>
                <span class="suggestion-chip" style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:30px;padding:8px 18px;color:rgba(255,255,255,0.7);font-size:14px;cursor:default;">🎯 SWE interview prep</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Suggestions as buttons (actual functionality)
        suggestions = [
            ("📁", "Organize my downloads"),
            ("💻", "Debug my Python code"),
            ("💰", "Analyze my spending"),
            ("🎯", "SWE interview prep"),
        ]
        cols = st.columns(4)
        for col, (icon, text) in zip(cols, suggestions):
            with col:
                if st.button(f"{icon} {text}", use_container_width=True, key=f"sug_{text}"):
                    st.session_state.chat_history.append({"role": "user", "content": text})
                    with st.spinner("🧠 Thinking..."):
                        try:
                            result = run_master_router(text, context={"chat_history": st.session_state.chat_history})
                            st.session_state.chat_history.append({"role": "assistant", "content": result["response"]})
                        except Exception as e:
                            st.session_state.chat_history.append({"role": "assistant", "content": f"⚠️ Error: {e}"})
                    save_current_chat()
                    st.rerun()
    else:
        # Chat messages
        for msg in chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat input
    user_msg = st.chat_input("Ask anything: organize files, debug code, analyze spending, interview prep...")
    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.spinner("🧠 Master Router analyzing..."):
            try:
                result = run_master_router(user_msg, context={"chat_history": st.session_state.chat_history})
                st.session_state.chat_history.append({"role": "assistant", "content": result["response"]})
            except Exception as e:
                st.session_state.chat_history.append({"role": "assistant", "content": f"⚠️ Error: {e}"})
        save_current_chat()
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# PRODUCTIVITY VIEW
# ═══════════════════════════════════════════════════════════════════════
def show_productivity():
    st.markdown("""
    <div style="text-align:center;margin-bottom:28px;">
        <h1 style="font-size:28px;font-weight:700;color:white;margin-bottom:4px;">🗂️ Productivity Hub</h1>
        <p style="color:rgba(255,255,255,0.4);font-size:14px;">Intelligent file analysis, auto-categorization, and organization</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        with st.container():
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            tab1, tab2 = st.tabs(["📤 Upload Files", "🔍 Scan & Organize"])
            with tab1:
                uploaded = st.file_uploader("Drop files into raw staging area", accept_multiple_files=True)
                if uploaded:
                    raw_dir = Path("data/raw_files")
                    raw_dir.mkdir(parents=True, exist_ok=True)
                    for f in uploaded:
                        (raw_dir / f.name).write_bytes(f.getvalue())
                    st.success(f"✅ Uploaded {len(uploaded)} file(s)")
            with tab2:
                dry_run = st.toggle("🔍 Dry Run (Preview only)", value=True)
                if st.button("🚀 Start Organization", type="primary", use_container_width=True, key="start_org_btn"):
                    with st.spinner("🗂️ Agent scanning..."):
                        files_info = analyze_files() if analyze_files else []
                        if files_info:
                            result = organize_files(files_info, dry_run=dry_run)
                            st.session_state.productivity_logs = result.get("logs", [])
                            if dry_run:
                                st.info(f"🔍 Preview: {result.get('moved', 0)} files would be organized into {len(result.get('categories', []))} categories.")
                            else:
                                st.success(f"✅ Organized {result.get('moved', 0)} files into {len(result.get('categories', []))} categories.")
                        else:
                            st.warning("📂 No files found in data/raw_files/")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.productivity_logs:
            with st.container():
                st.markdown("<div class='glass-card' style='margin-top:16px;'>", unsafe_allow_html=True)
                st.markdown("### 📋 Execution Log")
                st.code("\n".join(st.session_state.productivity_logs[-50:]), language="bash")
                st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        with st.container():
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("### 📊 File Stats")
            files_info = analyze_files() if analyze_files else []
            if files_info:
                import pandas as pd
                df = pd.DataFrame(files_info)
                st.metric("Total Files", len(files_info))
                st.metric("Categories", len(df["category"].unique()))
                st.metric("Total Size", f"{df['size'].sum() / 1024:.1f} KB")
                try:
                    import plotly.express as px
                    fig = px.pie(df, names="category", color_discrete_sequence=px.colors.sequential.Plasma)
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e0ff', showlegend=False, margin=dict(t=30,b=0,l=0,r=0))
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    pass
            else:
                st.info("No files to analyze")
            st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# ACADEMICS VIEW
# ═══════════════════════════════════════════════════════════════════════
def show_academics():
    st.markdown("""
    <div style="text-align:center;margin-bottom:28px;">
        <h1 style="font-size:28px;font-weight:700;background:linear-gradient(135deg,#67e8f9,#a7f3d0);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px;">📚 Academic Studio</h1>
        <p style="color:rgba(255,255,255,0.4);font-size:14px;">Code debugging, research paper analysis, and intelligent Q&A</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💻 Code Debugger", "📄 PDF Assistant"])
    with tab1:
        with st.container():
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            code_input = st.text_area("Paste your code snippet", height=250, placeholder="# Paste Python, JavaScript, Java, C++, etc.\ndef example():\n    pass")
            lang = st.selectbox("Language", ["python", "javascript", "java", "cpp", "go", "rust", "sql"], index=0)
            if st.button("🔍 Debug & Analyze", type="primary", use_container_width=True, key="debug_btn"):
                if code_input.strip() and run_academics_agent:
                    with st.spinner("📚 Analyzing code..."):
                        try:
                            result = run_academics_agent(f"Debug this {lang} code:\n```{lang}\n{code_input}\n```", {})
                            st.markdown(result["response"])
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please paste some code first")
            st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        col1, col2 = st.columns([1, 2])
        with col1:
            with st.container():
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("### 📤 PDF Library")
                uploaded_pdf = st.file_uploader("Upload research paper (PDF)", type=["pdf"])
                if uploaded_pdf:
                    acad_dir = Path("data/academic_docs")
                    acad_dir.mkdir(parents=True, exist_ok=True)
                    (acad_dir / uploaded_pdf.name).write_bytes(uploaded_pdf.getvalue())
                    st.success(f"✅ Uploaded {uploaded_pdf.name}")
                pdfs = list_academic_pdfs() if list_academic_pdfs else []
                if pdfs:
                    st.markdown("**Available Papers:**")
                    for pdf in pdfs:
                        st.markdown(f"• {pdf['name']} ({pdf['size']})")
                else:
                    st.info("No papers uploaded yet")
                st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            with st.container():
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("### 🔬 Document Q&A")
                pdfs = list_academic_pdfs() if list_academic_pdfs else []
                if pdfs:
                    selected = st.selectbox("Select paper", [p["name"] for p in pdfs])
                    query = st.text_input("Ask a question or leave blank for summary", placeholder="What is the main contribution?")
                    if st.button("📖 Analyze Document", type="primary", use_container_width=True, key="analyze_doc_btn"):
                        with st.spinner("📚 Reading paper..."):
                            try:
                                from agents.academics import summarize_pdf
                                result = summarize_pdf(Path("data/academic_docs") / selected, query if query.strip() else None)
                                st.markdown(result)
                            except Exception as e:
                                st.error(f"Error: {e}")
                else:
                    st.info("Upload a PDF to begin analysis")
                st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# FINANCE VIEW
# ═══════════════════════════════════════════════════════════════════════
def show_finance():
    st.markdown("""
    <div style="text-align:center;margin-bottom:28px;">
        <h1 style="font-size:28px;font-weight:700;background:linear-gradient(135deg,#f472b6,#fb7185);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px;">💰 Finance Tracker</h1>
        <p style="color:rgba(255,255,255,0.4);font-size:14px;">Expense analysis, automated categorization, and budget intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.container():
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("### 📤 Bank Statements")
            uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
            if uploaded:
                fin_dir = Path("data/financial_docs")
                fin_dir.mkdir(parents=True, exist_ok=True)
                (fin_dir / uploaded.name).write_bytes(uploaded.getvalue())
                st.success(f"✅ Uploaded {uploaded.name}")
            if st.button("💹 Analyze Latest Statement", type="primary", use_container_width=True, key="analyze_stmt_btn"):
                with st.spinner("💰 Finance Agent crunching numbers..."):
                    try:
                        result = run_finance_agent("Analyze my spending", {})
                        st.session_state.finance_data = result
                    except Exception as e:
                        st.error(f"Error: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.finance_data and st.session_state.finance_data.get("metrics"):
            m = st.session_state.finance_data["metrics"]
            with st.container():
                st.markdown("<div class='glass-card' style='margin-top:16px;'>", unsafe_allow_html=True)
                st.metric("Net Flow", f"${m.get('net', 0):.2f}")
                st.metric("Total Expenses", f"${m.get('total_expenses', 0):.2f}")
                st.metric("Transactions", m.get("transaction_count", 0))
                st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        if st.session_state.finance_data:
            data = st.session_state.finance_data
            with st.container():
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("### 📊 Spending Breakdown")
                if data.get("metrics") and data["metrics"].get("by_category"):
                    import pandas as pd
                    cat_df = pd.DataFrame(data["metrics"]["by_category"])
                    try:
                        import plotly.express as px
                        fig = px.bar(cat_df, x="category", y="total", color="percentage", color_continuous_scale="Plasma",
                                    labels={"total": "Amount ($)", "category": "Category"})
                        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e0ff',
                                         xaxis_gridcolor='rgba(255,255,255,0.05)', yaxis_gridcolor='rgba(255,255,255,0.05)')
                        st.plotly_chart(fig, use_container_width=True)
                    except:
                        st.bar_chart(cat_df.set_index("category")["total"])
                st.markdown("</div>", unsafe_allow_html=True)

            with st.container():
                st.markdown("<div class='glass-card' style='margin-top:16px;'>", unsafe_allow_html=True)
                st.markdown("### 🧠 Advisor Report")
                if data.get("advice"):
                    st.markdown(data["advice"])
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown("<div class='glass-card' style='padding:60px 20px;text-align:center;'>", unsafe_allow_html=True)
                st.markdown("### 💰 Upload a bank statement to get started")
                st.markdown("<p style='color:rgba(255,255,255,0.3);'>The Finance Agent will auto-categorize transactions and generate personalized budget advice.</p>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# CAREER VIEW
# ═══════════════════════════════════════════════════════════════════════
def show_career():
    st.markdown("""
    <div style="text-align:center;margin-bottom:28px;">
        <h1 style="font-size:28px;font-weight:700;background:linear-gradient(135deg,#fb923c,#facc15);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px;">🎯 Career Prep</h1>
        <p style="color:rgba(255,255,255,0.4);font-size:14px;">Dynamic mock interviews with AI-powered evaluation and scoring</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        with st.container():
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("### ⚙️ Interview Settings")
            role = st.text_input("Target Role", value=st.session_state.career_session.get("role", "Software Engineer"))
            topic = st.selectbox("Question Type", ["technical", "behavioral", "system_design"],
                                index=["technical", "behavioral", "system_design"].index(st.session_state.career_session.get("topic", "technical")))
            difficulty = st.select_slider("Difficulty", options=["easy", "medium", "hard"], value="medium")
            st.session_state.career_session["role"] = role
            st.session_state.career_session["topic"] = topic

            if st.button("🎲 Generate Question", type="primary", use_container_width=True, key="gen_q_btn"):
                with st.spinner("🎯 Career Agent crafting question..."):
                    try:
                        from agents.career import generate_interview_question
                        q = generate_interview_question(role, topic, difficulty)
                        st.session_state.career_session["current_question"] = q
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.career_session.get("history"):
            with st.container():
                st.markdown("<div class='glass-card' style='margin-top:16px;'>", unsafe_allow_html=True)
                st.markdown("### 📈 Score History")
                try:
                    import pandas as pd
                    import plotly.express as px
                    hist_df = pd.DataFrame(st.session_state.career_session["history"])
                    fig = px.line(hist_df, x="attempt", y="score", markers=True, labels={"score": "Score (/50)", "attempt": "Attempt #"})
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e0ff',
                                     xaxis_gridcolor='rgba(255,255,255,0.05)', yaxis_gridcolor='rgba(255,255,255,0.05)')
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    pass
                st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        with st.container():
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown("### ❓ Current Question")
            current_q = st.session_state.career_session.get("current_question", "")
            if current_q:
                st.markdown(f"""
                <div style="background:rgba(99,102,241,0.06);border-left:4px solid #6366f1;padding:16px;border-radius:0 12px 12px 0;margin-bottom:20px;">
                    <div style="color:rgba(255,255,255,0.4);font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">{role} — {topic.title()}</div>
                    <div style="color:rgba(255,255,255,0.85);font-size:15px;font-weight:500;line-height:1.6;">{current_q}</div>
                </div>
                """, unsafe_allow_html=True)
                answer = st.text_area("Your Answer", height=200, placeholder="Type your response here...")
                if st.button("📝 Submit for Evaluation", use_container_width=True, key="submit_eval_btn"):
                    if answer.strip() and run_career_agent:
                        with st.spinner("🎯 Evaluating..."):
                            try:
                                result = run_career_agent(answer, {"career_session": st.session_state.career_session, "interview_role": role})
                                st.markdown(result["response"])
                                if result.get("score"):
                                    st.session_state.career_session["history"].append({
                                        "attempt": len(st.session_state.career_session["history"]) + 1,
                                        "score": result["score"], "role": role, "topic": topic,
                                    })
                            except Exception as e:
                                st.error(f"Error: {e}")
                    else:
                        st.warning("Please provide an answer first")
            else:
                st.markdown("""
                <div style="text-align:center;padding:40px 20px;color:rgba(255,255,255,0.3);">
                    <div style="font-size:40px;margin-bottom:16px;">🎯</div>
                    <div style="font-size:16px;font-weight:500;margin-bottom:8px;color:rgba(255,255,255,0.6);">Ready to practice?</div>
                    <div>Configure your settings and generate a question to begin your mock interview.</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# MAIN APP FLOW
# ═══════════════════════════════════════════════════════════════════════
if not st.session_state.authenticated:
    show_login_page()
else:
    render_sidebar()
    view = st.session_state.current_view
    if view == "chat":
        show_chat_view()
    elif view == "productivity":
        show_productivity()
    elif view == "academics":
        show_academics()
    elif view == "finance":
        show_finance()
    elif view == "career":
        show_career()