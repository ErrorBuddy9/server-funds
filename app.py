import streamlit as st
from st_gsheets_connection import GSheetsConnection
import pandas as pd
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

# --- DIRECT CONNECTION ---
# Using the URL directly in the code to bypass Secret formatting issues
SHEET_URL = "https://docs.google.com/spreadsheets/d/1tkGfZmFNIXhfl3gfj4EPTnA8Pt5R3yGcgpecR0uc4VA"

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    # This forces the app to look for the specific tab name
    return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)

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
            try:
                df = get_data("Users")
                if not df.empty and reg_user in df['Username'].values:
                    st.error("Username exists.")
                else:
                    new_row = pd.DataFrame([{"Username": reg_user, "Password": make_hashes(reg_pass)}])
                    updated = pd.concat([df, new_row], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=updated)
                    st.success("Account Created! Go to Sign In.")
            except Exception as e:
                st.error("Cannot access 'Users' tab. Check sheet name!")

    with tab1: # SIGN IN
        u = st.text_input("Username", key="s1")
        p = st.text_input("Password", type="password", key="s2")
        if st.button("Log In"):
            try:
                df = get_data("Users")
                if not df.empty and u in df['Username'].values:
                    stored_pass = df[df['Username'] == u]['Password'].values[0]
                    if make_hashes(p) == str(stored_pass):
                        st.session_state['logged_in'] = True
                        st.session_state['user'] = u
                        st.rerun()
                st.error("Invalid Username or Password.")
            except:
                st.error("Connection Failed. Is the sheet link correct?")
    st.stop()

# --- APP CONTENT ---
st.title(f"💰 Welcome, {st.session_state['user']}")
try:
    funds_df = get_data("Funds")
    st.dataframe(funds_df, use_container_width=True)
except:
    st.warning("Could not load Fund history.")
