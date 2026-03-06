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

# --- GUI DESIGN (KEEPING YOUR ORIGINAL STYLE) ---
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
            data, count = supabase.table("users").insert({"username": reg_user, "password": hashed_pw}).execute()
            if data:
                st.success("Account Created! Go to Sign In.")
            else:
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
st.title(f"💰 Welcome, {st.session_state['user']}")

# Fetch Funds Data
funds_response = supabase.table("funds").select("*").execute()
if funds_response.data:
    df = pd.DataFrame(funds_response.data)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No fund records found.")
