import streamlit as st
from st_gsheets_connection import GSheetsConnection
import pandas as pd
import hashlib

# --- PAGE CONFIG ---
st.set_page_config(page_title="Server Fund Manager", layout="wide")

# --- PASSWORD HASHING ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- LIQUID GLASS GUI DESIGN (macOS Style) ---
st.markdown("""
    <style>
    /* Dark Deep Base */
    .stApp {
        background: linear-gradient(135deg, #050510 0%, #101030 100%);
        color: #FFFFFF;
    }
    
    /* High-Gloss Metric Cards */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(30px) saturate(180%);
        -webkit-backdrop-filter: blur(30px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.2); 
        border-radius: 20px;
        padding: 22px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.3);
    }
    
    /* macOS-style Blue Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        background: linear-gradient(180deg, #007AFF 0%, #0056D2 100%);
        color: white;
        border: none;
        font-weight: 600;
        height: 3.2em;
        transition: 0.2s;
    }
    
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(0, 122, 255, 0.5);
    }

    /* Transparent Input Fields */
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- AUTHENTICATION SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Server Fund Access")
    auth_mode = st.tabs(["Sign In", "Register Account"])
    
    with auth_mode[1]: # REGISTER
        new_user = st.text_input("New Username", key="reg_user")
        new_pass = st.text_input("New Password", type="password", key="reg_pass")
        if st.button("Create Account"):
            try:
                user_df = conn.read(worksheet="Users", ttl=0)
                if not user_df.empty and new_user in user_df['Username'].values:
                    st.error("Username already taken.")
                else:
                    new_user_data = pd.DataFrame([{"Username": new_user, "Password": make_hashes(new_pass)}])
                    updated_users = pd.concat([user_df, new_user_data], ignore_index=True)
                    conn.update(worksheet="Users", data=updated_users)
                    st.success("Account created! Now Sign In.")
            except:
                st.error("Error: Check if the 'Users' tab exists in your Google Sheet.")

    with auth_mode[0]: # SIGN IN
        login_user = st.text_input("Username", key="log_user")
        login_pass = st.text_input("Password", type="password", key="log_pass")
        if st.button("Log In"):
            try:
                user_df = conn.read(worksheet="Users", ttl=0)
                if not user_df.empty and login_user in user_df['Username'].values:
                    correct_pass = user_df[user_df['Username'] == login_user]['Password'].values[0]
                    if make_hashes(login_pass) == correct_pass:
                        st.session_state['logged_in'] = True
                        st.session_state['user'] = login_user
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                else:
                    st.error("User not found.")
            except:
                st.error("Connection failed. Check your Secrets and Sheet Permissions.")
    st.stop()

# --- MAIN APP INTERFACE ---
st.sidebar.title("👤 Account")
st.sidebar.write(f"Active User: **{st.session_state['user']}**")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# Data Loading
try:
    df = conn.read(worksheet="Funds", ttl=0)
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)
except:
    df = pd.DataFrame(columns=["Type", "User", "Amount", "Note", "Date"])

st.title("📊 Server Treasury Dashboard")

# Analytics Calculations
total_in = df[df["Type"] == "Add"]["Amount"].sum()
total_out = df[df["Type"] == "Withdraw"]["Amount"].sum()
net_balance = total_in - total_out

m1, m2, m3 = st.columns(3)
m1.metric("Current Balance", f"${net_balance:,.2f}")
m2.metric("Total Collected", f"${total_in:,.2f}")
m3.metric("Total Expenses", f"${total_out:,.2f}")

st.divider()

# Input & Rankings
col_input, col_stats = st.columns([1, 1.5])

with col_input:
    st.subheader("Manage Funds")
    with st.form("transaction_form", clear_on_submit=True):
        t_type = st.radio("Action", ["Add", "Withdraw"], horizontal=True)
        t_amount = st.number_input("Amount ($)", min_value=0.0)
        t_note = st.text_input("Reason")
        
        if st.form_submit_button("Record Transaction"):
            new_data = pd.DataFrame([{
                "Type": t_type, 
                "User": st.session_state['user'], 
                "Amount": t_amount, 
                "Note": t_note, 
                "Date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
            }])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            conn.update(worksheet="Funds", data=updated_df)
            st.success("Transaction recorded!")
            st.rerun()

with col_stats:
    st.subheader("Contribution Leaderboard")
    if not df.empty and "Type" in df.columns:
        adds = df[df["Type"] == "Add"]
        if not adds.empty:
            rankings = adds.groupby("User")["Amount"].sum().sort_values(ascending=False).reset_index()
            st.dataframe(rankings, use_container_width=True, hide_index=True)
        else:
            st.info("No contributions recorded yet.")
    else:
        st.info("Leaderboard will appear after first contribution.")

st.subheader("📜 Recent Activity")
st.dataframe(df.sort_index(ascending=False), use_container_width=True)
