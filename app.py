import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="Intelligence Treasury v4", layout="wide", initial_sidebar_state="collapsed")

# --- INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- UTILS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- CSS: THE LIQUID GLASS ENGINE + ARROW KILLER + NOTIFICATION JS ---
st.markdown(f"""
    <script>
    function notifyMe(title, message) {{
        if (!("Notification" in window)) {{
            console.log("This browser does not support desktop notification");
        }} else if (Notification.permission === "granted") {{
            new Notification(title, {{body: message}});
        }} else if (Notification.permission !== "denied") {{
            Notification.requestPermission().then(function (permission) {{
                if (permission === "granted") {{
                    new Notification(title, {{body: message}});
                }}
            }});
        }}
    }}
    </script>
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
            url('https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=2070&auto=format&fit=crop');
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
    }}

    /* 4. LIQUID PROGRESS BARS (Pill Style) */
    .stProgress > div > div > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 50px;
        height: 8px;
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
    
    [data-testid="stMetricValue"] {{ font-size: 1.6rem !important; color: #00f2fe !important; }}

    /* 6. INPUT FIELD SYNC (Perfect Corners) */
    .stTextInput>div>div, .stNumberInput>div>div, .stSelectbox>div>div {{
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }}

    /* 7. BUTTONS */
    .stButton>button {{
        width: 100%;
        border-radius: 12px !important;
        background: linear-gradient(135deg, rgba(0, 242, 254, 0.1) 0%, rgba(58, 71, 213, 0.1) 100%) !important;
        border: 1px solid rgba(0, 242, 254, 0.3) !important;
        color: white !important;
        font-weight: 700 !important;
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        background: rgba(0, 242, 254, 0.2) !important;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.3);
    }}
    </style>
    """, unsafe_allow_html=True)

def trigger_notification(title, msg):
    st.markdown(f"<script>notifyMe('{title}', '{msg}')</script>", unsafe_allow_html=True)

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; margin-top: 150px;'>VAULT ACCESS</h1>", unsafe_allow_html=True)
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
    df['net'] = df.apply(lambda x: x['amount'] if x['type']=='Add' else -x['amount'], axis=1)
    
    in_amt = df[df["type"] == "Add"]["amount"].sum()
    out_amt = df[df["type"] == "Withdraw"]["amount"].sum()
    bal = in_amt - out_amt

    # --- WEEKLY COMPARISON LOGIC ---
    now = datetime.now()
    this_week_start = now - timedelta(days=now.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    this_week_adds = df[(df['created_at'] >= this_week_start) & (df['type'] == 'Add')]['amount'].sum()
    last_week_adds = df[(df['created_at'] >= last_week_start) & (df['created_at'] < this_week_start) & (df['type'] == 'Add')]['amount'].sum()
    
    # --- AI PREDICTION LOGIC ---
    last_30_days = df[df['created_at'] > (now - timedelta(days=30))]
    daily_avg = last_30_days['net'].sum() / 30 if not last_30_days.empty else 0
else:
    in_amt = out_amt = bal = this_week_adds = last_week_adds = daily_avg = 0

# --- DASHBOARD HEADER ---
st.markdown('<div style="display:flex; align-items:center;"><span style="font-family: Arial; font-size:32px; color:#00f2fe; margin-right:15px; filter:drop-shadow(0 0 10px #00f2fe);">✦</span><h1 style="margin:0;">Intelligence Treasury</h1></div>', unsafe_allow_html=True)

# MINIMIZED TARGETS (Global)
target_res = supabase.table("targets").select("*").eq("is_archived", False).execute()
if target_res.data:
    t_cols = st.columns(len(target_res.data))
    for i, t in enumerate(target_res.data):
        goal = float(t['target_amount'])
        prog = min(max(bal / goal, 0), 1.0)
        with t_cols[i]:
            st.markdown(f"<p style='font-size:0.75rem; margin-bottom:-10px;'>{t['goal_name']} • {int(prog*100)}%</p>", unsafe_allow_html=True)
            st.progress(prog)
            if prog >= 1.0:
                trigger_notification("🎯 Goal Reached!", f"Target {t['goal_name']} is 100% funded.")

# --- ANALYTICS & AI INSIGHTS ---
st.write("")
c_metrics, c_ai = st.columns([1.5, 1])

with c_metrics:
    m1, m2, m3 = st.columns(3)
    m1.metric("Balance", f"LKR {bal:,.0f}")
    m2.metric("Weekly Adds", f"LKR {this_week_adds:,.0f}", delta=f"{this_week_adds - last_week_adds:,.0f} vs Last Wk")
    m3.metric("Total Expenses", f"LKR {out_amt:,.0f}")

with c_ai:
    if target_res.data and daily_avg > 0:
        t = target_res.data[0]
        rem = float(t['target_amount']) - bal
        if rem > 0:
            days = int(rem / daily_avg)
            finish = (datetime.now() + timedelta(days=days)).strftime("%b %d, %Y")
            st.markdown(f"<div style='background:rgba(0,242,254,0.05); padding:10px; border-radius:15px; border:1px solid rgba(0,242,254,0.2);'><p style='margin:0; font-size:0.8rem;'>🧠 <b>AI Projection:</b> '{t['goal_name']}' likely finished by <b>{finish}</b> ({days} days).</p></div>", unsafe_allow_html=True)

# --- CHARTS ---
st.write("")
col_chart, col_dist = st.columns([2, 1])
with col_chart:
    if not df.empty:
        df_sorted = df.sort_values("created_at")
        df_sorted['cumulative'] = df_sorted['net'].cumsum()
        fig = px.area(df_sorted, x="created_at", y="cumulative", title="Wealth Growth")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=250)
        st.plotly_chart(fig, use_container_width=True)

with col_dist:
    if not df.empty:
        fig_pie = px.pie(df, values='amount', names='type', hole=.6, title="Flow Distro")
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False, height=200)
        st.plotly_chart(fig_pie, use_container_width=True)

# --- FORMS ---
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
            trigger_notification("Sync Success", f"{tt}ed LKR {ta:,.0f} for {tn}")
            st.rerun()

with f2:
    with st.form("tg", clear_on_submit=True):
        st.markdown("#### 🎯 Set Global Goal")
        gn = st.text_input("Goal Name")
        ga = st.number_input("Target Amount", min_value=0.0)
        if st.form_submit_button("Launch Goal"):
            supabase.table("targets").insert({"goal_name": gn, "target_amount": ga, "created_by": user_now}).execute()
            st.rerun()

# --- LOG ---
st.write("")
st.markdown("#### 📜 Recent Activity")
if not df.empty:
    st.dataframe(df.sort_values("created_at", ascending=False).head(5), use_container_width=True, hide_index=True)

if st.sidebar.button("EXIT"):
    st.session_state.update({"logged_in": False})
    st.rerun()
