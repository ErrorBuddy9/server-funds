import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import hashlib

# --- PAGE CONFIG ---
st.set_page_config(page_title="Server Fund Manager", layout="wide")

# --- PASSWORD HASHING ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- LIQUID GLASS GUI DESIGN (Vibrant & Glossy) ---
st.markdown("""
    <style>
    /* Dark Gradient Base */
    .stApp {
        background: linear-gradient(135deg, #050510 0%, #101030 100%);
        color: #FFFFFF;
    }
    
    /* LIQUID GLASS Cards for Metrics */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05); /* Very Translucent */
        backdrop-filter: blur(25px) saturate(180%); /* Strong Blur & Saturation */
        -webkit-backdrop-filter: blur(25px) saturate(180%);
        
        /* Thin Border Highlight */
        border: 1px solid rgba(255, 255, 255, 0.15); 
        border-radius: 20px;
        padding: 20px;
        
        /* Multi-layered Glass Shadow and Inner Glow */
        box-shadow: 
            0 10px 30px rgba(0, 0, 0, 0.4),            /* Main Shadow */
            inset 0 1px 1px rgba(255, 255, 255, 0.3),   /* Top Light Edge */
            inset 0 -1px 1px rgba(0, 0, 0, 0.2);        /* Bottom Shadow Edge */
            
        transition: transform 0.2s ease-out, box-shadow 0.2s ease-out;
    }
    
    /* Metric Card Hover Interaction */
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 
            0 15px 40px rgba(0, 0, 0, 0.5),
            inset 0 1px 1px rgba(255, 255, 255, 0.4);
    }

    /* Vibrant Blue Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 14px;
        background: linear-gradient(180deg, #007AFF 0%, #0056D2 100%); /* macOS Blue */
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        font-weight: 600;
        height: 3em;
        transition: 0.2s;
    }
    
    .stButton>button:hover {
        opacity: 0.9;
        transform: scale(1.02);
    }

    /* Glass Input Styling */
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        color: white;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    /* Secondary Table Styling */
    .stDataFrame, .stTable {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Clean Divider */
    hr {
        border-color: rgba(255, 255, 255, 0.1);
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
    
    with auth_mode[1]: # SIGN UP
        with st.container():
            new_user = st.text_input("New Username", key="reg_user")
            new_pass = st.text_input("New Password", type="password", key="reg_pass")
            if st.button("Create Account"):
                user_df = conn.read(worksheet="Users")
                if new_user in user_df['Username'].values:
                    st.error("This username is already taken.")
                else:
                    new_user_data = pd.DataFrame([{"Username": new_user, "Password": make_hashes(new_pass)}])
                    updated_users = pd.concat([user_df, new_user_data], ignore_index=True)
                    conn.update(worksheet="Users", data=updated_users)
                    st.success("Registration successful! Please sign in.")

    with auth_mode[0]: # LOGIN
        login_user = st.text_input("Username", key="log_user")
        login_pass = st.text_input("Password", type="password", key="log_pass")
        if st.button("Log In"):
            user_df = conn.read(worksheet="Users")
            hashed_input = make_hashes(login_pass)
            if login_user in user_df['Username'].values:
                correct_pass = user_df[user_df['Username'] == login_user]['Password'].values[0]
                if hashed_input == correct_pass:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = login_user
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("User not found.")
    st.stop()

# --- MAIN APP INTERFACE ---
st.sidebar.title("👤 Profile")
st.sidebar.write(f"Logged in as: **{st.session_state['user']}**")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# Data Loading
df = conn.read(worksheet="Funds")
df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0)

st.title("📊 Server Treasury Dashboard")

# Summary Section
total_in = df[df["Type"] == "Add"]["Amount"].sum()
total_out = df[df["Type"] == "Withdraw"]["Amount"].sum()
net_balance = total_in - total_out

m1, m2, m3 = st.columns(3)
m1.metric("Current Balance", f"${net_balance:,.2f}")
m2.metric("Total Collected", f"${total_in:,.2f}")
m3.metric("Total Expenses", f"${total_out:,.2f}")

st.divider()

# Transaction Form
col_input, col_stats = st.columns([1, 1.5])

with col_input:
    st.subheader("Manage Funds")
    with st.form("transaction_form", clear_on_submit=True):
        t_type = st.radio("Action", ["Add", "Withdraw"], horizontal=True)
        t_amount = st.number_input("Amount ($)", min_value=0.0)
        t_note = st.text_input("Description (e.g., Hosting, Donation)")
        
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
            st.success("Transaction updated!")
            st.rerun()

with col_stats:
    st.subheader("Contribution Rankings")
    rankings = df[df["Type"] == "Add"].groupby("User")["Amount"].sum().sort_values(ascending=False).reset_index()
    st.dataframe(rankings, use_container_width=True, hide_index=True)

# History Section
st.subheader("📜 Recent Transactions")
st.dataframe(df.sort_index(ascending=False), use_container_width=True)
