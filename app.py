import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, timedelta, timezone
import numpy as np

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Intelligence Treasury v5", layout="wide", initial_sidebar_state="collapsed")

# --- 2. INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- 3. UTILS & AUTH ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- 4. CSS: LIQUID GLASS UI + DUAL LOGIN DESIGN ---
st.markdown(f"""
    <script>
    function notifyMe(title, message) {{
        if (!("Notification" in window)) {{
            console.log("Browser does not support notifications");
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

    /* AGGRESSIVE ARROW KILLER */
    [data-testid="collapsedControl"], .st-emotion-cache-6qob1r, .st-emotion-cache-1f3w014, header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    .block-container {{ padding-top: 1.5rem !important; }}

    /* LIQUID GLASS BACKGROUND */
    .stApp {{
        background: 
            radial-gradient(circle at 50% 50%, rgba(10, 10, 25, 0.85) 0%, rgba(0,0,0,0.97) 100%),
            url('https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2070&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif !important;
    }}
    
    /* GLASS PANELS */
    div[data-testid="stColumn"], div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {{
        background: rgba(255, 255, 255, 0.02) !important; 
        backdrop-filter: blur(55px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: 0 15px 35px rgba(0,0,0,0.6);
        transition: all 0.3s ease-in-out;
    }}

    div[data-testid="stColumn"]:hover {{
        border: 1px solid #00f2fe !important;
        box-shadow: 0 0 25px rgba(0, 242, 254, 0.25) !important;
    }}

    /* TYPOGRAPHY */
    h1, h2, h3, p, span, label, [data-testid="stMetricValue"] {{
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important; color: white !important;
    }}
    
    [data-testid="stMetricValue"] {{ font-size: 1.6rem !important; color: #00f2fe !important; }}

    /* INPUTS & BUTTONS */
    .stTextInput>div>div, .stNumberInput>div>div {{
        border-radius: 12px !important; background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; color: white !important;
    }}

    .stButton>button {{
        width: 100%; border-radius: 12px !important;
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.1) 0%, rgba(58, 71, 213, 0.1) 100%) !important;
        border: 1px solid rgba(0, 242, 254, 0.3) !important; color: white !important;
        font-weight: 700 !important; transition: 0.3s;
    }}
    </style>
    """, unsafe_allow_html=True)

def trigger_notification(title, msg):
    st.markdown(f"<script>notifyMe('{title}', '{msg}')</script>", unsafe_allow_html=True)

# --- 5. DUAL-SIDED AUTH SYSTEM ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 80px; letter-spacing: 5px;'>TREASURY PROTOCOL</h1>", unsafe_allow_html=True)
    st.write("")
    
    col_login, col_signup = st.columns(2)
    
    with col_login:
        st.markdown("### 🔑 LOGIN")
        u_log = st.text_input("Username", key="login_u")
        p_log = st.text_input("Password", type="password", key="login_p")
        if st.button("AUTHORIZE ACCESS"):
            res = supabase.table("users").select("*").eq("username", u_log).execute()
            if res.data and make_hashes(p_log) == res.data[0]['password']:
                st.session_state['logged_in'], st.session_state['user'] = True, u_log
                st.rerun()
            else:
                st.error("Invalid Credentials")

    with col_signup:
        st.markdown("### 📝 SIGN UP")
        u_sign = st.text_input("New Username", key="sign_u")
        p_sign = st.text_input("New Password", type="password", key="sign_p")
        if st.button("CREATE ACCOUNT"):
            if u_sign and p_sign:
                try:
                    supabase.table("users").insert({"username": u_sign, "password": make_hashes(p_sign)}).execute()
                    st.success("Account Created! You can now log in.")
                except:
                    st.error("Username already exists.")
            else:
                st.warning("Please fill all fields.")
    st.stop()

# --- 6. DATA & CALCULATIONS (REMAINING CODE REMAINS UNCHANGED) ---
user_now = st.session_state['user']
funds_res = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_res.data) if funds_res.data else pd.DataFrame()
now = datetime.now(timezone.utc)

if not df.empty:
    df["amount"] = pd.to_numeric(df["amount"])
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df['net'] = df.apply(lambda x: x['amount'] if x['type']=='Add' else -x['amount'], axis=1)
    
    in_amt, out_amt = df[df["type"] == "Add"]["amount"].sum(), df[df["type"] == "Withdraw"]["amount"].sum()
    bal = in_amt - out_amt

    # --- WEEKLY STATS ---
    this_week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
    last_week_start = this_week_start - timedelta(days=7)
    this_week_adds = df[(df['created_at'] >= this_week_start) & (df['type'] == 'Add')]['amount'].sum()
    last_week_adds = df[(df['created_at'] >= last_week_start) & (df['created_at'] < this_week_start) & (df['type'] == 'Add')]['amount'].sum()
    
    # --- AI VELOCITY ---
    first_entry = df['created_at'].min()
    total_hours = (now - first_entry).total_seconds() / 3600
    velocity = bal / total_hours if total_hours > 0 else 0
    daily_avg = df[df['created_at'] > (now - timedelta(days=30))]['net'].sum() / 30
else:
    in_amt = out_amt = bal = this_week_adds = last_week_adds = velocity = daily_avg = 0

# --- 7. DASHBOARD HEADER ---
st.markdown('<div style="display:flex; align-items:center;"><span style="font-family: Arial; font-size:32px; color:#00f2fe; margin-right:15px; filter:drop-shadow(0 0 10px #00f2fe);">✦</span><h1 style="margin:0;">Global Intelligence Hub</h1></div>', unsafe_allow_html=True)

# TARGET PILLS
target_res = supabase.table("targets").select("*").eq("is_archived", False).execute()
if target_res.data:
    t_cols = st.columns(len(target_res.data))
    for i, t in enumerate(target_res.data):
        goal = float(t['target_amount'])
        prog = min(max(bal / goal, 0), 1.0)
        with t_cols[i]:
            st.markdown(f"<p style='font-size:0.7rem; margin-bottom:-10px;'>{t['goal_name']} • {int(prog*100)}%</p>", unsafe_allow_html=True)
            st.progress(prog)
            if prog >= 1.0: trigger_notification("🎯 Goal Reached!", f"{t['goal_name']} is 100% funded.")

# --- 8. CORE ANALYTICS ---
st.write("")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Net Balance", f"LKR {bal:,.0f}")
m2.metric("Weekly Adds", f"LKR {this_week_adds:,.0f}", delta=f"{this_week_adds - last_week_adds:,.0f} vs L/W")
m3.metric("Growth Velocity", f"{velocity:,.2f} / hr")
m4.metric("Expenses", f"LKR {out_amt:,.0f}")

# --- 9. AI INSIGHTS & CHARTS ---
st.write("")
col_chart, col_ai = st.columns([2, 1])

with col_chart:
    if not df.empty:
        df_sorted = df.sort_values("created_at")
        df_sorted['cumulative'] = df_sorted['net'].cumsum()
        fig = px.area(df_sorted, x="created_at", y="cumulative", title="Financial Growth Timeline")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=300)
        st.plotly_chart(fig, use_container_width=True)

with col_ai:
    st.markdown("#### 🧠 AI Projections")
    if target_res.data and daily_avg > 0:
        t = target_res.data[0]
        rem = float(t['target_amount']) - bal
        if rem > 0:
            days = int(rem / daily_avg)
            finish = (now + timedelta(days=days)).strftime("%b %d, %Y")
            st.info(f"Objective '{t['goal_name']}' likely secured by **{finish}** ({days} days).")
        else: st.success("Target achieved. Set new objectives.")
    else: st.write("AI sync in progress... Need more data.")

# --- 10. INTERACTION FORMS ---
st.write("")
f1, f2 = st.columns(2)
with f1:
    with st.form("tx", clear_on_submit=True):
        st.markdown("#### 📥 Log Transaction")
        tt = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
        ta = st.number_input("Amount", min_value=0.0)
        tn = st.text_input("Note")
        if st.form_submit_button("Sync to Cloud"):
            supabase.table("funds").insert({"type": tt, "user": user_now, "amount": ta, "note": tn}).execute()
            trigger_notification("Vault Updated", f"{tt}: LKR {ta:,.0f}")
            st.rerun()

with f2:
    with st.form("tg", clear_on_submit=True):
        st.markdown("#### 🎯 Create Global Target")
        gn = st.text_input("Goal Name")
        ga = st.number_input("Target Amount", min_value=0.0)
        if st.form_submit_button("Deploy Goal"):
            supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
            st.rerun()

# --- 11. RECENT LOG ---
st.markdown("#### 📜 Activity Feed")
if not df.empty:
    st.dataframe(df.sort_values("created_at", ascending=False).head(5), use_container_width=True, hide_index=True)

if st.sidebar.button("LOGOUT"):
    st.session_state.update({"logged_in": False})
    st.rerun()
