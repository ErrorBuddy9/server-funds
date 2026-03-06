import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Glass Treasury", layout="wide", initial_sidebar_state="collapsed")

# --- INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- FETCH UI THEME ---
# Using a high-quality abstract glass background
bg_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop"

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- ULTIMATE GLASSMORPHISM CSS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');

    /* Background Setup */
    .stApp {{
        background-image: url('{bg_url}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Poppins', sans-serif !important;
    }}
    
    /* Super Curved Bold Typography */
    h1, h2, h3, p, span, label, .stMetric div {{
        font-family: 'Poppins', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
        color: white !important;
    }}

    /* Floating Glass Cards with heavy blur */
    div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {{
        background: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(30px) saturate(200%) !important;
        -webkit-backdrop-filter: blur(30px) saturate(200%) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 30px !important; /* Maximum Curves */
        padding: 25px !important;
        margin-bottom: 20px;
        box-shadow: 0 15px 35px 0 rgba(0, 0, 0, 0.4);
    }}

    /* Progress Bar Liquid Style */
    .stProgress > div > div > div {{
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px;
        height: 12px;
    }}
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, #00dbde 0%, #fc00ff 100%) !important;
        border-radius: 20px;
    }}

    /* Button Styling with Hover Effects */
    .stButton>button {{
        border-radius: 20px !important;
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
        font-weight: 800 !important;
        padding: 12px 24px !important;
        transition: 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}
    .stButton>button:hover {{
        background: rgba(255, 255, 255, 0.25) !important;
        transform: scale(1.05);
        box-shadow: 0 0 20px rgba(255, 255, 255, 0.2);
    }}

    /* Icon styling */
    .tx-icon {{
        font-size: 24px;
        margin-right: 10px;
    }}

    /* Metric refinement */
    div[data-testid="stMetricValue"] {{
        font-size: 2.2rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 80px; font-size: 3rem;'>💎 LIQUID</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["L O G I N", "J O I N"])
        with tab1:
            u = st.text_input("User", placeholder="Enter username...")
            p = st.text_input("Pass", type="password", placeholder="Enter password...")
            if st.button("UNLOCK DASHBOARD"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and make_hashes(p) == res.data[0]['password']:
                    st.session_state['logged_in'], st.session_state['user'] = True, u
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
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
st.markdown(f"<h1><span class='tx-icon'>💠</span>{user_now}'s Treasury</h1>", unsafe_allow_html=True)

# 1. Independent Targets
target_res = supabase.table("targets").select("*").eq("created_by", user_now).eq("is_archived", False).execute()
if target_res.data:
    for target in target_res.data:
        goal = float(target['target_amount'])
        progress = min(max(bal / goal, 0), 1.0)
        st.markdown(f"<p style='margin-bottom:-10px;'>🎯 <b>{target['goal_name']}</b> <span style='float:right; color:#fc00ff;'>Rs. {bal:,.0f} / {goal:,.0f}</span></p>", unsafe_allow_html=True)
        st.progress(progress)
        if progress >= 1.0:
            st.balloons()
            supabase.table("targets").update({"is_archived": True}).eq("id", target['id']).execute()
            st.rerun()

# 2. Main Metrics
st.write("")
m1, m2, m3 = st.columns(3)
m1.metric("Available", f"Rs. {bal:,.0f}")
m2.metric("Total In", f"Rs. {in_amt:,.0f}")
m3.metric("Total Out", f"Rs. {out_amt:,.0f}")

# 3. Forms
st.write("")
col1, col2 = st.columns(2)
with col1:
    with st.form("tx"):
        st.markdown("### <span class='tx-icon'>💸</span>Record Transaction", unsafe_allow_html=True)
        tt = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
        ta = st.number_input("Amount (LKR)", step=500.0)
        tn = st.text_input("Note/Reason")
        if st.form_submit_button("SUBMIT"):
            supabase.table("funds").insert({"type": tt, "user": user_now, "amount": ta, "note": tn}).execute()
            st.rerun()

with col2:
    with st.form("tg"):
        st.markdown("### <span class='tx-icon'>🎯</span>New Savings Goal", unsafe_allow_html=True)
        gn = st.text_input("What are we saving for?")
        ga = st.number_input("Target (LKR)", step=1000.0)
        if st.form_submit_button("ACTIVATE TARGET"):
            supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
            st.rerun()

# 4. Styled History
st.markdown("### <span class='tx-icon'>📜</span>Activity Log", unsafe_allow_html=True)
if not df.empty:
    # Adding emojis to the dataframe for visual flair
    df_styled = df.sort_values("created_at", ascending=False).copy()
    df_styled['type'] = df_styled['type'].apply(lambda x: f"📥 {x}" if x == "Add" else f"📤 {x}")
    st.dataframe(df_styled[['type', 'user', 'amount', 'note', 'created_at']], use_container_width=True, hide_index=True)

if st.sidebar.button("LOGOUT"):
    st.session_state.update({"logged_in": False})
    st.rerun()
