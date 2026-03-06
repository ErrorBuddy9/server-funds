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

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- CUSTOM LIQUID GLASS CSS ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp { 
        background: radial-gradient(circle at top right, #1a1a3a, #050510); 
        color: #FFFFFF; 
    }
    
    /* Compact Glass Target Card */
    .mini-target {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px 15px;
        margin-bottom: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Metric Styling */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 15px !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    }

    /* Input Glass Style */
    .stTextInput>div>div, .stNumberInput>div>div, .stSelectbox>div>div {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: white !important;
    }

    /* Floating Action Button Style */
    .stButton>button {
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%);
        border: none; border-radius: 8px; color: white;
        font-weight: bold; transition: 0.3s;
    }
    .stButton>button:hover {
        box-shadow: 0 0 15px rgba(0, 198, 255, 0.6);
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h2 style='text-align: center; margin-top: 50px;'>💎 Liquid Treasury</h2>", unsafe_allow_html=True)
    with st.container():
        cols = st.columns([1, 2, 1])
        with cols[1]:
            tab1, tab2 = st.tabs(["Login", "Register"])
            with tab1:
                u = st.text_input("User", key="s1")
                p = st.text_input("Pass", type="password", key="s2")
                if st.button("Access Dashboard"):
                    res = supabase.table("users").select("*").eq("username", u).execute()
                    if res.data and make_hashes(p) == res.data[0]['password']:
                        st.session_state['logged_in'], st.session_state['user'] = True, u
                        st.rerun()
            with tab2:
                reg_u = st.text_input("New User", key="r1")
                reg_p = st.text_input("New Pass", type="password", key="r2")
                if st.button("Create"):
                    supabase.table("users").insert({"username": reg_u, "password": make_hashes(reg_p)}).execute()
                    st.success("Ready!")
    st.stop()

# --- DASHBOARD LOGIC ---
user_now = st.session_state['user']

# Fetch Data
funds_res = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_res.data) if funds_res.data else pd.DataFrame()
if not df.empty: df["amount"] = pd.to_numeric(df["amount"])

# Calculations
in_amt = df[df["type"] == "Add"]["amount"].sum() if not df.empty else 0
out_amt = df[df["type"] == "Withdraw"]["amount"].sum() if not df.empty else 0
bal = in_amt - out_amt

# --- 1. COMPACT TARGETS SECTION ---
st.markdown(f"### 🎯 Goals: {user_now}")
target_res = supabase.table("targets").select("*").eq("created_by", user_now).eq("is_archived", False).execute()

if target_res.data:
    for target in target_res.data:
        goal = float(target['target_amount'])
        progress = min(max(bal / goal, 0), 1.0)
        
        # Mini Header for Target
        st.markdown(f"""
            <div class="mini-target">
                <span style="font-weight: bold;">{target['goal_name']}</span>
                <span style="color: #00C6FF;">Rs. {bal:,.0f} / {goal:,.0f}</span>
            </div>
        """, unsafe_allow_html=True)
        st.progress(progress)
        
        if progress >= 1.0:
            st.balloons()
            supabase.table("targets").update({"is_archived": True}).eq("id", target['id']).execute()
            st.rerun()
else:
    st.markdown("<p style='opacity: 0.5;'>No active targets.</p>", unsafe_allow_html=True)

# --- 2. STATS ---
st.write(" ")
m1, m2, m3 = st.columns(3)
m1.metric("Current Balance", f"Rs. {bal:,.0f}")
m2.metric("Total In", f"Rs. {in_amt:,.0f}")
m3.metric("Total Out", f"Rs. {out_amt:,.0f}")

# --- 3. INPUTS (Side by Side) ---
st.write(" ")
c1, c2 = st.columns(2)
with c1:
    with st.expander("📝 Record Transaction", expanded=True):
        with st.form("tx", clear_on_submit=True):
            ttype = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
            tamt = st.number_input("Amount", step=500.0)
            tnote = st.text_input("Note")
            if st.form_submit_button("Confirm"):
                supabase.table("funds").insert({"type": ttype, "user": user_now, "amount": tamt, "note": tnote}).execute()
                st.rerun()

with c2:
    with st.expander("🎯 Set New Goal", expanded=True):
        with st.form("tg", clear_on_submit=True):
            g_name = st.text_input("Goal Name")
            g_amt = st.number_input("Target", step=1000.0)
            if st.form_submit_button("Set Target"):
                supabase.table("targets").insert({"goal_name": g_name, "target_amount": g_amt, "created_by": user_now}).execute()
                st.rerun()

# --- 4. HISTORY & ANALYTICS ---
st.markdown("### 📊 Activity")
if not df.empty:
    # Small Chart
    fig = px.area(df, x="created_at", y="amount", color="type", height=200)
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
    
    # History
    st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True, hide_index=True)

if st.sidebar.button("Logout"):
    st.session_state.update({"logged_in": False})
    st.rerun()
