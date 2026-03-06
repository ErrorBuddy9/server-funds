import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Treasury Pro", layout="wide", initial_sidebar_state="collapsed")

# --- INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- THEME BACKGROUND (Darker, sophisticated gradient) ---
bg_url = "https://images.unsplash.com/photo-1614850523296-d8c1af93d400?q=80&w=2070&auto=format&fit=crop"

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- ENHANCED VISION PRO GLASS CSS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* Sophisticated Darker Background */
    .stApp {{
        background-image: url('{bg_url}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* Global Text: Lower Brightness, High Contrast */
    h1, h2, h3, p, span, label, .stMetric div {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        color: rgba(255, 255, 255, 0.95) !important;
        letter-spacing: -0.02em;
    }}

    /* Deep Glass Cards (Vision Pro Style) */
    div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {{
        background: rgba(20, 20, 20, 0.3) !important; /* Darker glass base */
        backdrop-filter: blur(45px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(45px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important; /* Soft white edge */
        border-radius: 28px !important;
        padding: 22px !important;
        margin-bottom: 18px;
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.4);
    }}

    /* Refined Progress Bar (Command Bar Style) */
    .stProgress > div > div > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 50px;
        height: 10px;
    }}
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, #515ada 0%, #efd5ff 100%) !important;
        border-radius: 50px;
    }}

    /* Button: Subtle & Frosted */
    .stButton>button {{
        border-radius: 18px !important;
        background: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
        transition: 0.3s ease;
    }}
    .stButton>button:hover {{
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        transform: translateY(-1px);
    }}

    /* Minimal Metric Labels */
    div[data-testid="stMetricLabel"] {{
        opacity: 0.7;
        font-size: 0.9rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 100px; opacity: 0.9;'>Treasury Pro</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        tab1, tab2 = st.tabs(["Log In", "Join"])
        with tab1:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Unlock Access"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and make_hashes(p) == res.data[0]['password']:
                    st.session_state['logged_in'], st.session_state['user'] = True, u
                    st.rerun()
    st.stop()

# --- DATA FETCH ---
user_now = st.session_state['user']
funds_res = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_res.data) if funds_res.data else pd.DataFrame()
if not df.empty: df["amount"] = pd.to_numeric(df["amount"])

in_amt = df[df["type"] == "Add"]["amount"].sum() if not df.empty else 0
out_amt = df[df["type"] == "Withdraw"]["amount"].sum() if not df.empty else 0
bal = in_amt - out_amt

# --- DASHBOARD UI ---
st.markdown(f"<h1>🛡️ {user_now}'s Treasury</h1>", unsafe_allow_html=True)

# 1. Targets (Minimalist Progress)
target_res = supabase.table("targets").select("*").eq("created_by", user_now).eq("is_archived", False).execute()
if target_res.data:
    for target in target_res.data:
        goal = float(target['target_amount'])
        progress = min(max(bal / goal, 0), 1.0)
        st.markdown(f"<p style='margin-bottom:-10px; font-size: 0.9rem;'>🎯 <b>{target['goal_name']}</b> <span style='float:right; opacity:0.6;'>Rs. {bal:,.0f} / {goal:,.0f}</span></p>", unsafe_allow_html=True)
        st.progress(progress)
        if progress >= 1.0:
            st.balloons()
            supabase.table("targets").update({"is_archived": True}).eq("id", target['id']).execute()
            st.rerun()

# 2. Key Metrics
st.write("")
m1, m2, m3 = st.columns(3)
m1.metric("Current Balance", f"Rs. {bal:,.0f}")
m2.metric("Total In", f"Rs. {in_amt:,.0f}")
m3.metric("Total Out", f"Rs. {out_amt:,.0f}")

# 3. Actions
st.write("")
col1, col2 = st.columns(2)
with col1:
    with st.form("tx", clear_on_submit=True):
        st.markdown("### 📥 Record Flow")
        tt = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
        ta = st.number_input("Amount (LKR)", step=500.0)
        tn = st.text_input("Note")
        if st.form_submit_button("Confirm Entry"):
            supabase.table("funds").insert({"type": tt, "user": user_now, "amount": ta, "note": tn}).execute()
            st.rerun()

with col2:
    with st.form("tg", clear_on_submit=True):
        st.markdown("### 🎯 New Target")
        gn = st.text_input("Objective")
        ga = st.number_input("Target (LKR)", step=1000.0)
        if st.form_submit_button("Set Goal"):
            supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
            st.rerun()

# 4. History Log
st.markdown("### 📜 Transaction Log")
if not df.empty:
    df_styled = df.sort_values("created_at", ascending=False).copy()
    st.dataframe(df_styled[['type', 'user', 'amount', 'note', 'created_at']], use_container_width=True, hide_index=True)

if st.sidebar.button("Log Out"):
    st.session_state.update({"logged_in": False})
    st.rerun()
