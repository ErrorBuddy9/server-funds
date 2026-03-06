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

# --- GUI DESIGN (LIQUID GLASS) ---
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
    /* Style the dataframe to match */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
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
                # Inserting into 'users' table
                supabase.table("users").insert({"username": reg_user, "password": hashed_pw}).execute()
                st.success("Account Created! Go to Sign In.")
            except:
                st.error("Error: Username might already be taken.")

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

# --- MAIN DASHBOARD ---
st.title(f"💰 Server Treasury")
st.write(f"Logged in as: **{st.session_state['user']}**")

# 1. Fetch Funds Data
funds_response = supabase.table("funds").select("*").execute()
if funds_response.data:
    df = pd.DataFrame(funds_response.data)
    df["amount"] = pd.to_numeric(df["amount"])
else:
    df = pd.DataFrame(columns=["id", "type", "user", "amount", "note", "created_at"])

# 2. Calculate Metrics
total_in = df[df["type"] == "Add"]["amount"].sum()
total_out = df[df["type"] == "Withdraw"]["amount"].sum()
current_balance = total_in - total_out

m1, m2, m3 = st.columns(3)
m1.metric("Current Balance", f"${current_balance:,.2f}")
m2.metric("Total Collected", f"${total_in:,.2f}")
m3.metric("Total Spent", f"${total_out:,.2f}")

st.divider()

# 3. Transaction Form and Leaderboard
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📝 New Transaction")
    with st.form("fund_form", clear_on_submit=True):
        t_type = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
        t_amt = st.number_input("Amount ($)", min_value=0.0, step=1.0)
        t_note = st.text_input("Note / Purpose")
        
        if st.form_submit_button("Submit"):
            if t_amt > 0:
                new_data = {
                    "type": t_type,
                    "user": st.session_state['user'],
                    "amount": t_amt,
                    "note": t_note
                }
                supabase.table("funds").insert(new_data).execute()
                st.success("Transaction Recorded!")
                st.rerun()
            else:
                st.warning("Please enter an amount greater than 0.")

with col2:
    st.subheader("🏆 Leaderboard (Top Contributors)")
    if not df.empty:
        # Show top users who added funds
        leaders = df[df["type"] == "Add"].groupby("user")["amount"].sum().sort_values(ascending=False).reset_index()
        st.dataframe(leaders, use_container_width=True, hide_index=True)
    else:
        st.info("No data yet.")

# 4. History Table
st.subheader("📜 Recent Activity")
if not df.empty:
    # Show newest transactions at the top
    st.dataframe(df.sort_values("id", ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("No transactions recorded.")

# Logout in sidebar
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()
