import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib

# --- PAGE CONFIG ---
st.set_page_config(page_title="Server Fund Manager", layout="wide")

# --- INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- PASSWORD HASHING ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- GUI DESIGN ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #050510 0%, #101030 100%); color: #FFFFFF; }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 20px;
        padding: 20px;
    }
    .stButton>button {
        width: 100%; border-radius: 12px;
        background: linear-gradient(180deg, #007AFF 0%, #0056D2 100%);
        color: white; border: none; font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Server Fund Access")
    tab1, tab2 = st.tabs(["Sign In", "Register Account"])
    
    with tab2: # REGISTER
        reg_user = st.text_input("New Username", key="r1")
        reg_pass = st.text_input("New Password", type="password", key="r2")
        if st.button("Create Account"):
            hashed_pw = make_hashes(reg_pass)
            try:
                response = supabase.table("users").insert({"username": reg_user, "password": hashed_pw}).execute()
                st.success("Account Created! Go to Sign In.")
            except:
                st.error("Error creating account. Username might be taken.")

    with tab1: # SIGN IN
        u = st.text_input("Username", key="s1")
        p = st.text_input("Password", type="password", key="s2")
        if st.button("Log In"):
            response = supabase.table("users").select("*").eq("username", u).execute()
            if response.data:
                stored_hash = response.data[0]['password']
                if make_hashes(p) == stored_hash:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = u
                    st.rerun()
            st.error("Invalid Username or Password.")
    st.stop()

# --- MAIN APP ---
st.title(f"💰 Server Treasury Dashboard")
st.write(f"Logged in as: **{st.session_state['user']}**")

# 1. Fetch Data
funds_response = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_response.data) if funds_response.data else pd.DataFrame(columns=["type", "user", "amount", "note", "created_at"])

# 2. Analytics & Metrics
if not df.empty:
    df["amount"] = pd.to_numeric(df["amount"])
    total_in = df[df["type"] == "Add"]["amount"].sum()
    total_out = df[df["type"] == "Withdraw"]["amount"].sum()
    balance = total_in - total_out
else:
    total_in, total_out, balance = 0, 0, 0

m1, m2, m3 = st.columns(3)
m1.metric("Current Balance", f"${balance:,.2f}")
m2.metric("Total Contributions", f"${total_in:,.2f}")
m3.metric("Total Expenses", f"${total_out:,.2f}")

st.divider()

# 3. Form & Stats Layout
col_form, col_leader = st.columns([1, 1.5])

with col_form:
    st.subheader("📝 Record Transaction")
    with st.form("tx_form", clear_on_submit=True):
        t_type = st.radio("Action", ["Add", "Withdraw"], horizontal=True)
        t_amt = st.number_input("Amount ($)", min_value=0.0, step=1.0)
        t_note = st.text_input("Note / Reason")
        
        if st.form_submit_button("Submit Transaction"):
            new_tx = {
                "type": t_type,
                "user": st.session_state['user'],
                "amount": t_amt,
                "note": t_note
            }
            supabase.table("funds").insert(new_tx).execute()
            st.success("Recorded!")
            st.rerun()

with col_leader:
    st.subheader("🏆 Top Contributors")
    if not df.empty:
        adds = df[df["type"] == "Add"]
        if not adds.empty:
            leaderboard = adds.groupby("user")["amount"].sum().sort_values(ascending=False).reset_index()
            st.dataframe(leaderboard, use_container_width=True, hide_index=True)
        else:
            st.info("No contributions yet.")
    else:
        st.info("Leaderboard will appear here.")

st.subheader("📜 Activity History")
if not df.empty:
    # Sort by ID descending to see newest first
    st.dataframe(df.sort_values("id", ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("No transactions recorded yet.")

if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()
