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

# --- THEME BACKGROUND (Darker, sophisticated dark-mesh) ---
bg_url = "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2070&auto=format&fit=crop"

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- ULTIMATE VISION PRO CSS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* Dark Immersive Background */
    .stApp {{
        background-image: url('{bg_url}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* Typography: Bold & Clean */
    h1, h2, h3, p, span, label {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        color: rgba(255, 255, 255, 0.9) !important;
        letter-spacing: -0.03em;
    }}

    /* Midnight Glass Cards (Darker & Deep Blur) */
    div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {{
        background: rgba(15, 15, 25, 0.4) !important; 
        backdrop-filter: blur(50px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(50px) saturate(150%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 30px !important;
        padding: 24px !important;
        margin-bottom: 20px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
    }}

    /* Entry Fields: Matching Label Colors */
    .stTextInput>div>div, .stNumberInput>div>div, .stSelectbox>div>div {{
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 14px !important;
        color: white !important;
        font-weight: 600 !important;
    }}

    /* Progress Bar (Matching the Deep Theme) */
    .stProgress > div > div > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 50px;
        height: 8px;
    }}
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, #3a47d5 0%, #00d2ff 100%) !important;
        border-radius: 50px;
    }}

    /* Button: Frosted & Subtle */
    .stButton>button {{
        border-radius: 16px !important;
        background: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        font-weight: 700 !important;
        transition: 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .stButton>button:hover {{
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }}

    /* Custom Header Icon Styling */
    .header-box {{
        display: flex;
        align-items: center;
        gap: 15px;
    }}
    .shield-icon {{
        background: linear-gradient(135deg, #3a47d5, #00d2ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 40px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 100px;'>ACCESS TREASURY</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        tab1, tab2 = st.tabs(["Log In", "Join"])
        with tab1:
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Unlock"):
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
st.markdown(f"""
    <div class="header-box">
        <div class="shield-icon">✦</div>
        <h1>{user_now}'s Treasury</h1>
    </div>
    """, unsafe_allow_html=True)

# 1. Targets
target_res = supabase.table("targets").select("*").eq("created_by", user_now).eq("is_archived", False).execute()
if target_res.data:
    for target in target_res.data:
        goal = float(target['target_amount'])
        progress = min(max(bal / goal, 0), 1.0)
        st.markdown(f"<p style='margin-bottom:-12px; font-size: 0.85rem; opacity: 0.8;'><b>{target['goal_name']}</b> <span style='float:right;'>LKR {bal:,.0f} / {goal:,.0f}</span></p>", unsafe_allow_html=True)
        st.progress(progress)
        if progress >= 1.0:
            st.balloons()
            supabase.table("targets").update({"is_archived": True}).eq("id", target['id']).execute()
            st.rerun()

# 2. Key Metrics
st.write("")
m1, m2, m3 = st.columns(3)
m1.metric("Available", f"LKR {bal:,.0f}")
m2.metric("Total In", f"LKR {in_amt:,.0f}")
m3.metric("Total Out", f"LKR {out_amt:,.0f}")

# 3. Forms
st.write("")
col1, col2 = st.columns(2)
with col1:
    with st.form("tx", clear_on_submit=True):
        st.markdown("### 📥 Record Flow")
        tt = st.radio("Transaction Type", ["Add", "Withdraw"], horizontal=True)
        ta = st.number_input("Amount (LKR)", step=500.0)
        tn = st.text_input("Note")
        if st.form_submit_button("Confirm Entry"):
            supabase.table("funds").insert({"type": tt, "user": user_now, "amount": ta, "note": tn}).execute()
            st.rerun()

with col2:
    with st.form("tg", clear_on_submit=True):
        st.markdown("### 🎯 New Target")
        gn = st.text_input("Objective")
        ga = st.number_input("Target Amount (LKR)", step=1000.0)
        if st.form_submit_button("Set Goal"):
            supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
            st.rerun()

# 4. History Log
st.markdown("### 📜 History")
if not df.empty:
    df_styled = df.sort_values("created_at", ascending=False).copy()
    st.dataframe(df_styled[['type', 'user', 'amount', 'note', 'created_at']], use_container_width=True, hide_index=True)

if st.sidebar.button("Log Out"):
    st.session_state.update({"logged_in": False})
    st.rerun()
