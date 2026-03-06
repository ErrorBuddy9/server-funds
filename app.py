import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Server Fund Manager", layout="wide")

# --- INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- GUI DESIGN (ENHANCED LIQUID GLASS) ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #050510 0%, #101030 100%); color: #FFFFFF; }
    
    /* Glass Cards */
    div[data-testid="stMetric"], .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 20px;
    }

    /* Target Box */
    .target-card {
        background: rgba(0, 122, 255, 0.15);
        border: 1px solid #007AFF;
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        margin-bottom: 10px;
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
    st.markdown("<h1 style='text-align: center;'>💎 Server Treasury</h1>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["Sign In", "Register"])
    with t2:
        reg_u = st.text_input("Username", key="r1").strip()
        reg_p = st.text_input("Password", type="password", key="r2")
        if st.button("Create Account"):
            if reg_u and reg_p:
                supabase.table("users").insert({"username": reg_u, "password": make_hashes(reg_p)}).execute()
                st.success("Account created! Go to Sign In.")
    with t1:
        u = st.text_input("Username", key="s1").strip()
        p = st.text_input("Password", type="password", key="s2")
        if st.button("Log In"):
            res = supabase.table("users").select("*").eq("username", u).execute()
            if res.data and make_hashes(p) == res.data[0]['password']:
                st.session_state['logged_in'] = True
                st.session_state['user'] = u
                st.rerun()
            st.error("Invalid credentials.")
    st.stop()

# --- APP LOGIC ---
user_now = st.session_state['user']

# 1. Fetch Funds Data
funds_res = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_res.data) if funds_res.data else pd.DataFrame()
if not df.empty: df["amount"] = pd.to_numeric(df["amount"])

# 2. Independent Targets (Top of Page)
st.title("💰 Server Dashboard")
st.subheader(f"Targets for {user_now}")

target_res = supabase.table("targets").select("*").eq("created_by", user_now).eq("is_archived", False).execute()

if target_res.data:
    for target in target_res.data:
        # Calculate current server balance for progress
        total_in = df[df["type"] == "Add"]["amount"].sum() if not df.empty else 0
        total_out = df[df["type"] == "Withdraw"]["amount"].sum() if not df.empty else 0
        current_bal = total_in - total_out
        
        goal = float(target['target_amount'])
        progress = min(max(current_bal / goal, 0), 1.0)
        
        st.markdown(f"""<div class="target-card">
            <h3>🎯 {target['goal_name']}</h3>
            <p>Goal: Rs. {goal:,.2f} | Current Balance: Rs. {current_bal:,.2f}</p>
        </div>""", unsafe_allow_html=True)
        st.progress(progress)
        
        if progress >= 1.0:
            st.balloons()
            st.success(f"Goal '{target['goal_name']}' Completed!")
            # ARCHIVE INSTEAD OF DELETE
            supabase.table("targets").update({"is_archived": True}).eq("id", target['id']).execute()
            st.rerun()
else:
    st.info("No active targets. Set one below!")

# 3. Main Metrics
st.divider()
in_amt = df[df["type"] == "Add"]["amount"].sum() if not df.empty else 0
out_amt = df[df["type"] == "Withdraw"]["amount"].sum() if not df.empty else 0
bal = in_amt - out_amt

m1, m2, m3 = st.columns(3)
m1.metric("Balance", f"Rs. {bal:,.2f}")
m2.metric("Total In", f"Rs. {in_amt:,.2f}")
m3.metric("Total Out", f"Rs. {out_amt:,.2f}")

# 4. Input Section
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("📝 Record Transaction")
    with st.form("tx_form", clear_on_submit=True):
        ttype = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
        tamt = st.number_input("Amount (LKR)", min_value=0.0, step=100.0)
        tnote = st.text_input("Note")
        if st.form_submit_button("Submit"):
            supabase.table("funds").insert({"type": ttype, "user": user_now, "amount": tamt, "note": tnote}).execute()
            st.rerun()

with c2:
    st.subheader("🎯 Set New Target")
    with st.form("target_form", clear_on_submit=True):
        g_name = st.text_input("Goal Name")
        g_amt = st.number_input("Goal Amount (Rs.)", min_value=0.0, step=500.0)
        if st.form_submit_button("Create My Goal"):
            supabase.table("targets").insert({"goal_name": g_name, "target_amount": g_amt, "created_by": user_now}).execute()
            st.rerun()

# 5. Analytics & History (Bottom)
st.divider()
st.subheader("📊 Analytics & History")

if not df.empty:
    # Personal Impact Text
    user_contrib = df[(df["user"] == user_now) & (df["type"] == "Add")]["amount"].sum()
    total_contrib = df[df["type"] == "Add"]["amount"].sum()
    percent = (user_contrib / total_contrib * 100) if total_contrib > 0 else 0
    
    st.info(f"✨ **Personal Impact:** You have contributed **Rs. {user_contrib:,.2f}** ({percent:.1f}% of total funds).")

    # Charts
    fig = px.bar(df, x="created_at", y="amount", color="type", title="Cash Flow Timeline")
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
    st.plotly_chart(fig, use_container_width=True)

    # History Table with style
    st.write("📜 **Recent Activity**")
    def color_type(val):
        color = '#25D366' if val == 'Add' else '#FF3B30'
        return f'color: {color}; font-weight: bold;'
    
    st.dataframe(df.sort_values("created_at", ascending=False).style.applymap(color_type, subset=['type']), use_container_width=True)

if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()
