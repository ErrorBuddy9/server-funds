import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import hashlib

# --- PAGE CONFIG ---
st.set_page_config(page_title="Server Fund Manager", layout="wide")

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

# --- NEW STABLE CONNECTION ---
@st.cache_resource
def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # This uses the public link directly for simplicity
    gc = gspread.public_authorize("https://docs.google.com/spreadsheets/d/1tkGfZmFNIXhfl3gfj4EPTnA8Pt5R3yGcgpecR0uc4VA")
    return gc.open_by_key("1tkGfZmFNIXhfl3gfj4EPTnA8Pt5R3yGcgpecR0uc4VA")

try:
    sh = get_gsheet_client()
    user_sheet = sh.worksheet("Users")
    fund_sheet = sh.worksheet("Funds")
except Exception as e:
    st.error("Connection Failed. Please ensure the Google Sheet is shared with 'Anyone with the link' as Editor.")
    st.stop()

# --- AUTH SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Server Fund Access")
    auth_mode = st.tabs(["Sign In", "Register"])
    
    with auth_mode[1]: # REGISTER
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            users = pd.DataFrame(user_sheet.get_all_records())
            if not users.empty and new_user in users['Username'].values:
                st.error("User exists.")
            else:
                user_sheet.append_row([new_user, make_hashes(new_pass)])
                st.success("Success! Now Sign In.")

    with auth_mode[0]: # SIGN IN
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Log In"):
            users = pd.DataFrame(user_sheet.get_all_records())
            if not users.empty and u in users['Username'].values:
                correct_p = users[users['Username'] == u]['Password'].values[0]
                if make_hashes(p) == correct_p:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = u
                    st.rerun()
            st.error("Invalid Login.")
    st.stop()

# --- MAIN DASHBOARD ---
st.title("📊 Server Treasury")
df = pd.DataFrame(fund_sheet.get_all_records())
df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)

# Metrics
total = df[df["Type"] == "Add"]["Amount"].sum() - df[df["Type"] == "Withdraw"]["Amount"].sum()
st.metric("Current Balance", f"${total:,.2f}")

# Transaction Form
with st.form("add_fund"):
    t_type = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
    amt = st.number_input("Amount", min_value=0.0)
    note = st.text_input("Note")
    if st.form_submit_button("Submit"):
        fund_sheet.append_row([t_type, st.session_state['user'], amt, note, pd.Timestamp.now().strftime("%Y-%m-%d")])
        st.rerun()

st.subheader("📜 History")
st.dataframe(df, use_container_width=True)
