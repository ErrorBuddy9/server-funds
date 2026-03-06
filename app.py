import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Treasury Glass Pro", layout="wide", initial_sidebar_state="collapsed")

# --- INITIALIZE SUPABASE ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- FETCH UI THEME (The Background Image) ---
ui_res = supabase.table("ui_settings").select("bg_image_url").execute()
default_bg = "https://raw.githubusercontent.com/m4rehan/glassmorphism/main/glass-bg.jpg" # Fallback
bg_url = ui_res.data[0]['bg_image_url'] if ui_res.data else default_bg

# --- PASSWORD HASHING ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- FULL GLASSMORPHISM CSS ---
st.markdown(f"""
    <style>
    /* Full Page Background Image */
    .stApp {{
        background-image: url('{bg_url}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    
    /* GLOBAL GLASSMOPRHISM RULES
       (Applies transparency and blur to containers) 
    */
    .main .block-container {{
        background: transparent !important;
    }}

    /* This targets Streamlit's structural columns to make them float */
    div[data-testid="stColumn"] {{
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px); /* The main blur effect */
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.15); /* Glass edge */
        border-radius: 20px;
        padding: 20px !important;
        margin: 10px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2); /* Floating shadow */
    }}

    /* Text & Input styling within glass elements */
    h1, h2, h3, p, div {{
        color: white !important;
        font-family: 'Inter', sans-serif;
    }}
    
    /* Glass Input Fields */
    .stTextInput>div>div, .stNumberInput>div>div, .stSelectbox>div>div {{
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px;
        color: white !important;
    }}
    
    /* Target Progress Box (Mini-Header) */
    .mini-target-glass {{
        background: rgba(0, 198, 255, 0.1);
        border-radius: 12px;
        padding: 8px;
        text-align: center;
        margin-bottom: 5px;
        border: 1px solid rgba(0, 198, 255, 0.2);
    }}

    /* Floating Blue Button Style */
    .stButton>button {{
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%);
        border: none; border-radius: 8px; color: white;
        font-weight: bold; transition: 0.3s;
        margin-top: 10px;
    }}
    .stButton>button:hover {{
        box-shadow: 0 0 15px rgba(0, 198, 255, 0.5);
        transform: translateY(-2px);
    }}
    
    /* Chart and Dataframe styling */
    .stPlotlyChart {{ background: transparent !important; }}
    .stDataFrame {{ background: transparent !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- AUTH SYSTEM (Keep original logic) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h2 style='text-align: center; color: white;'>💎 Liquid Treasury</h2>", unsafe_allow_html=True)
    with st.container():
        # Float the login box in the center
        login_cols = st.columns([1, 1.5, 1])
        with login_cols[1]:
            st.markdown("<div style='background: rgba(255,255,255,0.05); backdrop-filter: blur(20px); padding: 30px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
            u = st.text_input("User")
            p = st.text_input("Password", type="password")
            if st.button("Unlock Dashboard"):
                res = supabase.table("users").select("*").eq("username", u).execute()
                if res.data and make_hashes(p) == res.data[0]['password']:
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = u
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- APP LOGIC ---
user_now = st.session_state['user']

# Fetch Data
funds_res = supabase.table("funds").select("*").execute()
df = pd.DataFrame(funds_res.data) if funds_res.data else pd.DataFrame()
if not df.empty: df["amount"] = pd.to_numeric(df["amount"])

# Calculations
in_amt = df[df["type"] == "Add"]["amount"].sum() if not df.empty else 0
out_amt = df[df["type"] == "Withdraw"]["amount"].sum() if not df.empty else 0
bal = in_amt - out_amt

# --- 1. COMPACT GLASS TARGETS SECTION ---
st.title("💰 Server Dashboard")
st.write(f"Targets for **{user_now}**")

target_res = supabase.table("targets").select("*").eq("created_by", user_now).eq("is_archived", False).execute()

if target_res.data:
    for target in target_res.data:
        goal = float(target['target_amount'])
        progress = min(max(bal / goal, 0), 1.0)
        
        # Mini Header for Target
        st.markdown(f"""
            <div class="mini-target-glass">
                <span style="font-weight: bold;">🎯 {target['goal_name']}</span>
                <span style="color: #00C6FF; float: right;">Rs. {bal:,.0f} / {goal:,.0f}</span>
            </div>
        """, unsafe_allow_html=True)
        st.progress(progress)
        
        if progress >= 1.0:
            st.balloons()
            supabase.table("targets").update({"is_archived": True}).eq("id", target['id']).execute()
            st.rerun()
else:
    st.write("No active targets.")

st.divider()

# --- 2. MAIN STATS ---
# These columns will automatically get the glass styling from the global CSS rules.
m_col1, m_col2, m_col3 = st.columns(3)
m_col1.metric("Current Balance", f"Rs. {bal:,.0f}")
m_col2.metric("Total Collected", f"Rs. {in_amt:,.0f}")
m_col3.metric("Total Spent", f"Rs. {out_amt:,.0f}")

st.write(" ")

# --- 3. INPUT SECTIONS (Floating side-by-side) ---
c1, c2 = st.columns(2)
with c1:
    st.subheader("📝 Record Transaction")
    with st.form("tx_form", clear_on_submit=True):
        ttype = st.radio("Type", ["Add", "Withdraw"], horizontal=True)
        tamt = st.number_input("Amount (LKR)", min_value=0.0, step=100.0)
        tnote = st.text_input("Note")
        if st.form_submit_button("Confirm Transaction"):
            supabase.table("funds").insert({"type": ttype, "user": user_now, "amount": tamt, "note": tnote}).execute()
            st.rerun()

with c2:
    st.subheader("🎯 Set New Target")
    with st.form("target_form", clear_on_submit=True):
        g_name = st.text_input("Goal Name")
        g_amt = st.number_input("Goal Amount (Rs.)", min_value=0.0, step=500.0)
        if st.form_submit_button("Set Goal"):
            supabase.table("targets").insert({"goal_name": g_name, "target_amount": g_amt, "created_by": user_now}).execute()
            st.rerun()

st.write(" ")

# --- 4. HISTORY (BOTTOM GLASS) ---
st.subheader("📊 Activity")
h_col = st.columns(1)[0]
with h_col:
    if not df.empty:
        # Mini Timeline
        fig = px.area(df, x="created_at", y="amount", color="type", height=150)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Style Type Column
        def color_type(val):
            color = '#25D366' if val == 'Add' else '#FF3B30'
            return f'color: {color}; font-weight: bold;'
        
        # Glass Dataframe
        st.dataframe(df.sort_values("created_at", ascending=False).style.applymap(color_type, subset=['type']), use_container_width=True, hide_index=True)

if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()
