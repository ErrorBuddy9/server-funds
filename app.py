import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, timedelta, timezone
import numpy as np

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- 2. INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- 3. UTILS & AUTH ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 4. CSS: LIQUID GLASS UI + ARROW REMOVAL ---
st.markdown(f"""
    <script>
    function notifyMe(title, message) {{
        if (!("Notification" in window)) {{
            console.log("Notifications not supported");
        }} else if (Notification.permission === "granted") {{
            new Notification(title, {{body: message}});
        }} else if (Notification.permission !== "denied") {{
            Notification.requestPermission().then(function (p) {{
                if (p === "granted") new Notification(title, {{body: message}});
            }});
        }}
    }}
    </script>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* ARROW KILLER */
    [data-testid="collapsedControl"], .st-emotion-cache-6qob1r, .st-emotion-cache-1f3w014, header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    .block-container {{ padding-top: 1.5rem !important; }}

    /* LIQUID GLASS THEME */
    .stApp {{
        background: 
            radial-gradient(circle at 50% 50%, rgba(10, 10, 25, 0.85) 0%, rgba(0,0,0,0.97) 100%),
            url('https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* UNIVERSAL GLASS CARD DESIGN */
    div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div, .stDataFrame {{
        background: rgba(255, 255, 255, 0.02) !important; 
        backdrop-filter: blur(55px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        transition: all 0.3s ease-in-out;
    }}

    div[data-testid="stColumn"]:hover, .stDataFrame:hover {{
        border: 1px solid #00f2fe !important;
        box-shadow: 0 0 25px rgba(0, 242, 254, 0.25) !important;
    }}

    h1, h2, h3, p, span, label, [data-testid="stMetricValue"] {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important; color: white !important;
    }}
    
    [data-testid="stMetricValue"] {{ font-size: 1.6rem !important; color: #00f2fe !important; }}

    .stButton>button {{
        width: 100%; border-radius: 12px !important;
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.1) 0%, rgba(58, 71, 213, 0.1) 100%) !important;
        border: 1px solid rgba(0, 242, 254, 0.3) !important; color: white !important;
        font-weight: 700 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

def trigger_notification(title, msg):
    st.markdown(f"<script>notifyMe('{title}', '{msg}')</script>", unsafe_allow_html=True)

# --- 5. AUTH SYSTEM ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 80px;'>ACCESS PORTAL</h1>", unsafe_allow_html=True)
    st.write("")
    col_login, col_signup = st.columns(2)
    with col_login:
        st.markdown("### 🔑 LOGIN")
        u_log = st.text_input("Username", key="login_u")
        p_log = st.text_input("Password", type="password", key="login_p")
        if st.button("SIGN IN"):
            res = supabase.table("users").select("*").eq("username", u_log).execute()
            if res.data and make_hashes(p_log) == res.data[0]['password']:
                st.session_state['logged_in'], st.session_state['user'] = True, u_log
                st.rerun()
            else: st.error("Access Denied")
    with col_signup:
        st.markdown("### 📝 REGISTER")
        u_sign = st.text_input("New Username", key="sign_u")
        p_sign = st.text_input("New Password", type="password", key="sign_p")
        if st.button("CREATE ACCOUNT"):
            if u_sign and p_sign:
                try:
                    supabase.table("users").insert({"username": u_sign, "password": make_hashes(p_sign)}).execute()
                    st.success("Registration successful.")
                except: st.error("Username taken.")
    st.stop()

# --- 6. DATA PROCESSING ---
user_now = st.session_state['user']
funds_res = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_res.data) if funds_res.data else pd.DataFrame()
now = datetime.now(timezone.utc)

if not df.empty:
    df["amount"] = pd.to_numeric(df["amount"])
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df['net'] = df.apply(lambda x: x['amount'] if x['type']=='Add' else -x['amount'], axis=1)
    bal = df['net'].sum()
    this_week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
    this_week_adds = df[(df['created_at'] >= this_week_start) & (df['type'] == 'Add')]['amount'].sum()
    daily_avg = df[df['created_at'] > (now - timedelta(days=30))]['net'].sum() / 30
else:
    bal = this_week_adds = daily_avg = 0

# --- 7. DASHBOARD MAIN HEADER ---
st.markdown('<div style="display:flex; align-items:center;"><span style="font-family: Arial; font-size:32px; color:#00f2fe; margin-right:15px; filter:drop-shadow(0 0 10px #00f2fe);">✦</span><h1 style="margin:0;">Dashboard</h1></div>', unsafe_allow_html=True)
st.markdown(f"<p style='opacity:0.6; margin-top:-5px;'>Professional Financial Overview • User: <b>{user_now}</b></p>", unsafe_allow_html=True)

# TARGET PROGRESS
target_res = supabase.table("targets").select("*").eq("is_archived", False).execute()
if target_res.data:
    t_cols = st.columns(len(target_res.data))
    for i, t in enumerate(target_res.data):
        goal = float(t['target_amount'])
        prog = min(max(bal / goal, 0), 1.0)
        with t_cols[i]:
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: flex-end;'>
                    <span style='font-size: 0.8rem; font-weight: 600;'>{t['goal_name']}</span>
                    <span style='font-size: 0.65rem; opacity: 0.7;'>{int(bal):,}/{int(goal):,}</span>
                </div>
            """, unsafe_allow_html=True)
            st.progress(prog)

# --- 8. KEY METRICS & ANALYTICS ---
st.write("")
m1, m2, m3 = st.columns(3)
m1.metric("Current Balance", f"LKR {bal:,.0f}")
m2.metric("Weekly Activity", f"LKR {this_week_adds:,.0f}")
m3.metric("Daily Average", f"LKR {daily_avg:,.0f}")

st.write("")
col_chart, col_ai = st.columns([2, 1])
with col_chart:
    if not df.empty:
        df_sorted = df.sort_values("created_at")
        df_sorted['cumulative'] = df_sorted['net'].cumsum()
        fig = px.area(df_sorted, x="created_at", y="cumulative", title="Equity Growth Timeline")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=300)
        st.plotly_chart(fig, use_container_width=True)

with col_ai:
    st.markdown("#### 🧠 AI Insights")
    if target_res.data and daily_avg > 0:
        t = target_res.data[0]
        rem = float(t['target_amount']) - bal
        if rem > 0:
            finish = (now + timedelta(days=int(rem / daily_avg))).strftime("%b %d, %Y")
            st.info(f"Objective '{t['goal_name']}' estimated: **{finish}**")
        else: st.success("Target achieved.")

# --- 9. INTERACTION FORMS ---
st.write("")
f1, f2 = st.columns(2)
with f1:
    with st.form("tx", clear_on_submit=True):
        st.markdown("#### 📥 Log Entry")
        tt = st.radio("Action", ["Add", "Withdraw"], horizontal=True)
        ta = st.number_input("Value", min_value=0.0)
        tn = st.text_input("Reference")
        if st.form_submit_button("Record"):
            supabase.table("funds").insert({"type": tt, "user": user_now, "amount": ta, "note": tn}).execute()
            trigger_notification("System Update", f"Recorded {tt}: LKR {ta:,.0f}")
            st.rerun()

with f2:
    with st.form("tg", clear_on_submit=True):
        st.markdown("#### 🎯 Set Target")
        gn = st.text_input("Name")
        ga = st.number_input("Goal Value", min_value=0.0)
        if st.form_submit_button("Deploy"):
            supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
            st.rerun()

# --- 10. INTERACTION HISTORY (GLASSY CARD) ---
st.write("")
st.markdown("#### 📜 Interaction History")
if not df.empty:
    # Sort by newest first
    history_df = df.sort_values("created_at", ascending=False).head(10)
    # Rename columns for professional look
    history_df = history_df[["type", "amount", "note", "user", "created_at"]]
    history_df.columns = ["Type", "Amount (LKR)", "Reference", "User", "Timestamp"]
    
    # Render inside a glassy card container
    st.dataframe(
        history_df, 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("No transaction history available yet.")

if st.sidebar.button("EXIT"):
    st.session_state.update({"logged_in": False})
    st.rerun()
