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

# --- THEME BACKGROUND (High-End Dark Mesh) ---
bg_url = "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2070&auto=format&fit=crop"

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- CSS OVERHAUL: EYE COMFORT & FIXED CORNERS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

    /* 1. DARK GRADIENT OVERLAY (Comfort for eyes) */
    .stApp {{
        background: 
            linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)),
            url('{bg_url}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* 2. TEXT STYLING */
    h1, h2, h3, p, span, label {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        color: rgba(255, 255, 255, 0.9) !important;
    }}

    /* 3. ICON FIX: Uses System Font to ensure loading */
    .header-icon {{
        font-family: Arial, sans-serif !important; /* Force standard font */
        font-size: 32px;
        color: #00d2ff;
        margin-right: 15px;
        filter: drop-shadow(0 0 10px rgba(0, 210, 255, 0.4));
    }

    /* 4. FROSTED GLASS CARDS */
    div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {{
        background: rgba(255, 255, 255, 0.03) !important; 
        backdrop-filter: blur(40px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(40px) saturate(150%) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 28px !important;
        padding: 22px !important;
        margin-bottom: 20px;
    }}

    /* 5. FIXED ENTRY FIELD CORNERS & COLORS */
    .stTextInput>div>div, .stNumberInput>div>div, .stSelectbox>div>div {{
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 18px !important; /* Fixed smooth corners */
        color: white !important;
        font-weight: 600 !important;
    }}
    
    /* 6. PROGRESS BAR */
    .stProgress > div > div > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 20px;
        height: 10px;
    }}
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%) !important;
        border-radius: 20px;
    }}

    /* 7. PILL BUTTONS */
    .stButton>button {{
        border-radius: 20px !important;
        background: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: white !important;
        font-weight: 700 !important;
        transition: 0.3s;
        text-transform: uppercase;
    }}
    .stButton>button:hover {{
        background: rgba(255, 255, 255, 0.15) !important;
        transform: translateY(-2px);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 120px;'>CORE TREASURY</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 0.8, 1])
    with c2:
        tab1, tab2 = st.tabs(["Login", "Join"])
        with tab1:
            u = st.text_input("User ID")
            p = st.text_input("Key", type="password")
            if st.button("AUTHENTICATE"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and make_hashes(p) == res.data[0]['password']:
                    st.session_state['logged_in'], st.session_state['user'] = True, u
                    st.rerun()
    st.stop()

# --- DATA ---
user_now = st.session_state['user']
funds_res = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_res.data) if funds_res.data else pd.DataFrame()
if not df.empty: df["amount"] = pd.to_numeric(df["amount"])

in_amt = df[df["type"] == "Add"]["amount"].sum() if not df.empty else 0
out_amt = df[df["type"] == "Withdraw"]["amount"].sum() if not df.empty else 0
bal = in_amt - out_amt

# --- DASHBOARD ---
st.markdown(f'<h1><span class="header-icon">✦</span>{user_now}\'s Treasury</h1>', unsafe_allow_html=True)

# 1. Targets
target_res = supabase.table("targets").select("*").eq("created_by", user_now).eq("is_archived", False).execute()
if target_res.data:
    for target in target_res.data:
        goal = float(target['target_amount'])
        progress = min(max(bal / goal, 0), 1.0)
        st.markdown(f"<p style='margin-bottom:-12px; font-size: 0.8rem; opacity: 0.6;'><b>{target['goal_name']}</b> <span style='float:right;'>LKR {bal:,.0f} / {goal:,.0f}</span></p>", unsafe_allow_html=True)
        st.progress(progress)
        if progress >= 1.0:
            st.balloons()
            supabase.table("targets").update({"is_archived": True}).eq("id", target['id']).execute()
            st.rerun()

# 2. Metrics
st.write("")
m1, m2, m3 = st.columns(3)
m1.metric("Balance", f"LKR {bal:,.0f}")
m2.metric("Total In", f"LKR {in_amt:,.0f}")
m3.metric("Total Out", f"LKR {out_amt:,.0f}")

# 3. Forms
st.write("")
col1, col2 = st.columns(2)
with col1:
    with st.form("tx", clear_on_submit=True):
        st.markdown("### 📥 Record Flow")
        tt = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
        ta = st.number_input("Amount", min_value=0.0, step=500.0)
        tn = st.text_input("Note")
        if st.form_submit_button("Confirm Entry"):
            supabase.table("funds").insert({"type": tt, "user": user_now, "amount": ta, "note": tn}).execute()
            st.rerun()

with col2:
    with st.form("tg", clear_on_submit=True):
        st.markdown("### 🎯 New Target")
        gn = st.text_input("Goal Name")
        ga = st.number_input("Target Amount", min_value=0.0, step=1000.0)
        if st.form_submit_button("Set Goal"):
            supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
            st.rerun()

# 4. History
st.write("")
st.markdown("### 📜 History")
if not df.empty:
    st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)

if st.sidebar.button("LOGOUT"):
    st.session_state.update({"logged_in": False})
    st.rerun()
