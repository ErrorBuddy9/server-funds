import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="Pro Treasury Hub", layout="wide", initial_sidebar_state="collapsed")

# --- INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- THEME BACKGROUND ---
bg_url = "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2070&auto=format&fit=crop"

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- CSS: THE "ARROW KILLER" & GLASS UI ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

    /* 1. AGGRESSIVE SIDEBAR/ARROW REMOVAL */
    /* This targets the specific text and button container you are seeing in the top left */
    [data-testid="collapsedControl"], 
    .st-emotion-cache-6qob1r, 
    .st-emotion-cache-1f3w014, 
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    /* Remove padding created by the hidden header */
    .block-container {{
        padding-top: 2rem !important;
    }}

    /* 2. DARK COMFORT OVERLAY (94% Dark) */
    .stApp {{
        background: 
            linear-gradient(rgba(0, 0, 0, 0.94), rgba(0, 0, 0, 0.94)),
            url('{bg_url}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* 3. REFINED GLASS PANELS */
    div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {{
        background: rgba(255, 255, 255, 0.02) !important; 
        backdrop-filter: blur(40px) saturate(140%) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 20px !important;
        padding: 18px !important;
    }}

    /* 4. INPUT FIELD SYNC */
    .stTextInput>div>div, .stNumberInput>div>div, .stSelectbox>div>div {{
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }}

    /* 5. TYPOGRAPHY */
    h1, h2, h3, h4, p, span, label {{
        color: rgba(255, 255, 255, 0.95) !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em;
    }}

    /* 6. HEADER ICON (Native Font Fix) */
    .header-icon {{
        font-family: Arial, sans-serif !important;
        font-size: 30px;
        color: #00d2ff;
        margin-right: 12px;
        filter: drop-shadow(0 0 10px rgba(0, 210, 255, 0.5));
    }}
    </style>
    """, unsafe_allow_html=True)

# --- AUTH ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 150px;'>VAULT ACCESS</h1>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 0.8, 1])
    with c2:
        u = st.text_input("ID")
        p = st.text_input("KEY", type="password")
        if st.button("UNLOCK"):
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
    in_amt = df[df["type"] == "Add"]["amount"].sum()
    out_amt = df[df["type"] == "Withdraw"]["amount"].sum()
    bal = in_amt - out_amt
else:
    in_amt, out_amt, bal = 0, 0, 0

# --- HEADER & MINIMIZED TARGETS ---
st.markdown('<div style="display:flex; align-items:center;"><span class="header-icon">✦</span><h2 style="margin:0;">Intelligence Dashboard</h2></div>', unsafe_allow_html=True)

# Minimal Global Targets
target_res = supabase.table("targets").select("*").eq("is_archived", False).execute()
if target_res.data:
    cols = st.columns(len(target_res.data))
    for i, t in enumerate(target_res.data):
        goal = float(t['target_amount'])
        prog = min(max(bal / goal, 0), 1.0)
        with cols[i]:
            st.markdown(f"<p style='font-size:0.7rem; margin-bottom:-15px;'>{t['goal_name']} • {int(prog*100)}%</p>", unsafe_allow_html=True)
            st.progress(prog)

# --- ANALYTICS SECTION ---
st.write("")
col_main, col_stats = st.columns([2, 1])

with col_main:
    if not df.empty:
        df_sort = df.sort_values("created_at")
        df_sort['net'] = df_sort.apply(lambda x: x['amount'] if x['type']=='Add' else -x['amount'], axis=1)
        df_sort['cumulative'] = df_sort['net'].cumsum()
        
        fig = px.area(df_sort, x="created_at", y="cumulative", title="Financial Growth Curve")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                          font_color="white", height=280, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

with col_stats:
    st.metric("Net Liquidity", f"LKR {bal:,.0f}")
    st.metric("Total Inflow", f"LKR {in_amt:,.0f}")
    st.metric("Total Outflow", f"LKR {out_amt:,.0f}")

# --- NEW FEATURES: DISTRIBUTION CHART ---
st.write("")
col_pie, col_recent = st.columns([1, 2])

with col_pie:
    if not df.empty:
        fig_pie = px.pie(df, values='amount', names='type', hole=.4, title="Flow Distro")
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white", 
                             showlegend=False, height=200, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_pie, use_container_width=True)

with col_recent:
    st.markdown("#### 📜 Activity Feed")
    if not df.empty:
        st.dataframe(df.sort_values("created_at", ascending=False).head(5), 
                     use_container_width=True, hide_index=True)

# --- FORMS ---
st.write("")
f1, f2 = st.columns(2)
with f1:
    with st.form("tx"):
        st.markdown("#### 📥 Sync Transaction")
        tt = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
        ta = st.number_input("Amount", min_value=0.0)
        tn = st.text_input("Note")
        if st.form_submit_button("Push to Cloud"):
            supabase.table("funds").insert({"type": tt, "user": user_now, "amount": ta, "note": tn}).execute()
            st.rerun()

with f2:
    with st.form("tg"):
        st.markdown("#### 🎯 Deploy Global Goal")
        gn = st.text_input("Objective")
        ga = st.number_input("Target Amount", min_value=0.0)
        if st.form_submit_button("Create Target"):
            supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
            st.rerun()

if st.sidebar.button("LOGOUT"):
    st.session_state.update({"logged_in": False})
    st.rerun()
