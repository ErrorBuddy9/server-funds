import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Global Treasury v3", layout="wide", initial_sidebar_state="collapsed")

# --- INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- THEME BACKGROUND (Deep Dark Mesh) ---
bg_url = "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2070&auto=format&fit=crop"

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- THE LIQUID GLASS CSS ENGINE ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* 1. AGGRESSIVE ARROW KILLER (Top Left Fix) */
    [data-testid="collapsedControl"], 
    .st-emotion-cache-6qob1r, 
    .st-emotion-cache-1f3w014, 
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    .block-container {{ padding-top: 1.5rem !important; }}

    /* 2. LIQUID GLASS BACKGROUND (95% Dark Overlay) */
    .stApp {{
        background: 
            radial-gradient(circle at 50% 50%, rgba(10, 10, 25, 0.8) 0%, rgba(0,0,0,0.96) 100%),
            url('{bg_url}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* 3. NEON-ACCENTED GLASS PANELS */
    div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {{
        background: rgba(255, 255, 255, 0.02) !important; 
        backdrop-filter: blur(50px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(50px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: 0 15px 35px rgba(0,0,0,0.6);
        transition: transform 0.3s ease;
    }}

    /* 4. LIQUID PROGRESS BARS (Pill Style) */
    .stProgress > div > div > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 50px;
        height: 6px;
    }}
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, #00f2fe 0%, #3a47d5 100%) !important;
        border-radius: 50px;
        box-shadow: 0 0 10px rgba(0, 242, 254, 0.6);
    }}

    /* 5. TYPOGRAPHY & METRICS */
    h1, h2, h3, p, span, label, [data-testid="stMetricValue"] {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        color: white !important;
        letter-spacing: -0.04em;
    }}
    
    [data-testid="stMetricValue"] {{ font-size: 1.8rem !important; color: #00f2fe !important; }}

    /* 6. INPUT FIELD SYNC (Perfect Corners) */
    .stTextInput>div>div, .stNumberInput>div>div, .stSelectbox>div>div {{
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }}

    /* 7. LAUNCH BUTTON */
    .stButton>button {{
        width: 100%;
        border-radius: 12px !important;
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.1) 0%, rgba(58, 71, 213, 0.1) 100%) !important;
        border: 1px solid rgba(0, 242, 254, 0.3) !important;
        color: white !important;
        font-weight: 700 !important;
        padding: 10px 0 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background: rgba(0, 242, 254, 0.2) !important;
        border-color: #00f2fe;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.3);
    }}

    /* 8. HEADER ICON */
    .header-icon {{
        font-family: Arial, sans-serif !important;
        font-size: 32px;
        color: #00f2fe;
        margin-right: 15px;
        filter: drop-shadow(0 0 10px #00f2fe);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 150px;'>VAULT AUTHENTICATION</h1>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 0.8, 1])
    with c2:
        u = st.text_input("I D")
        p = st.text_input("K E Y", type="password")
        if st.button("AUTHENTICATE"):
            res = supabase.table("users").select("*").eq("username", u).execute()
            if res.data and make_hashes(p) == res.data[0]['password']:
                st.session_state['logged_in'], st.session_state['user'] = True, u
                st.rerun()
    st.stop()

# --- DATA PROCESSING ---
user_now = st.session_state['user']
funds_res = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_res.data) if funds_res.data else pd.DataFrame()
if not df.empty:
    df["amount"] = pd.to_numeric(df["amount"])
    df["created_at"] = pd.to_datetime(df["created_at"])

in_amt = df[df["type"] == "Add"]["amount"].sum() if not df.empty else 0
out_amt = df[df["type"] == "Withdraw"]["amount"].sum() if not df.empty else 0
bal = in_amt - out_amt

# --- HEADER & MINIMIZED TARGETS ---
st.markdown('<div style="display:flex; align-items:center;"><span class="header-icon">✦</span><h1 style="margin:0; font-size: 2.2rem;">GLOBAL TREASURY</h1></div>', unsafe_allow_html=True)

# Shared Targets (Pill Format)
st.write("")
target_res = supabase.table("targets").select("*").eq("is_archived", False).execute()
if target_res.data:
    t_cols = st.columns(len(target_res.data))
    for i, t in enumerate(target_res.data):
        goal = float(t['target_amount'])
        prog = min(max(bal / goal, 0), 1.0)
        with t_cols[i]:
            st.markdown(f"<p style='font-size:0.75rem; margin-bottom:-10px;'>✦ {t['goal_name']} <span style='float:right;'>{int(prog*100)}%</span></p>", unsafe_allow_html=True)
            st.progress(prog)

# --- ANALYTICS DASHBOARD ---
st.write("")
m1, m2, m3 = st.columns(3)
m1.metric("Current Balance", f"LKR {bal:,.0f}")
m2.metric("Total Inflow", f"LKR {in_amt:,.0f}")
m3.metric("Total Spent", f"LKR {out_amt:,.0f}")

st.write("")
col_chart, col_dist = st.columns([2, 1])

with col_chart:
    if not df.empty:
        df_sorted = df.sort_values("created_at")
        df_sorted['net'] = df_sorted.apply(lambda x: x['amount'] if x['type']=='Add' else -x['amount'], axis=1)
        df_sorted['cumulative'] = df_sorted['net'].cumsum()
        
        fig = px.area(df_sorted, x="created_at", y="cumulative", title="Wealth Growth")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                          font_color="white", height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

with col_dist:
    if not df.empty:
        fig_pie = px.pie(df, values='amount', names='type', hole=.6, title="Flow Distro")
        fig_pie.update_traces(marker=dict(colors=['#00f2fe', '#3a47d5']))
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white", 
                             showlegend=False, height=220, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

# --- TRANSACTION & GOAL FEED ---
st.write("")
c_log, c_forms = st.columns([1.5, 1])

with c_log:
    st.markdown("### 📜 Activity Log")
    if not df.empty:
        df_feed = df.sort_values("created_at", ascending=False).head(8)
        st.dataframe(df_feed[['type', 'user', 'amount', 'note']], use_container_width=True, hide_index=True)

with c_forms:
    with st.expander("📥 Add Transaction", expanded=True):
        with st.form("tx", clear_on_submit=True):
            tt = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
            ta = st.number_input("LKR Amount", min_value=0.0)
            tn = st.text_input("Note")
            if st.form_submit_button("Sync Data"):
                supabase.table("funds").insert({"type": tt, "user": user_now, "amount": ta, "note": tn}).execute()
                st.rerun()
    
    with st.expander("🎯 Set Shared Goal", expanded=False):
        with st.form("tg", clear_on_submit=True):
            gn = st.text_input("Goal Name")
            ga = st.number_input("Target LKR", min_value=0.0)
            if st.form_submit_button("Launch Goal"):
                supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
                st.rerun()

if st.sidebar.button("EXIT SYSTEM"):
    st.session_state.update({"logged_in": False})
    st.rerun()
