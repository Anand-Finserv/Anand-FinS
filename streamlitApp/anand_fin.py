import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import random
from datetime import datetime
import pytz
import time

# --- 1. PAGE CONFIG & CONNECTION ---
st.set_page_config(page_title="Anand Finserv", page_icon="📈", layout="wide")

# Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl="5s") # 5 second cache taaki data jaldi dikhe

def save_to_sheet(df_to_save):
    conn.update(data=df_to_save)
    st.cache_data.clear()

# --- 2. CSS FOR PROFESSIONAL LOOK ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; }
    .stButton>button { background-color: #007bff; color: white; border-radius: 8px; font-weight: bold; width: 100%; border:none; }
    .stButton>button:hover { background-color: #0056b3; border:none; color: white; }
    .stock-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 6px solid #007bff; margin-bottom: 15px; color: black !important; }
    .ticker-wrap { width: 100%; overflow: hidden; background: #111827; color: #4ade80; padding: 10px 0; font-family: monospace; font-weight: bold; }
    .ticker { display: flex; white-space: nowrap; animation: marquee 30s linear infinite; }
    @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    </style>
""", unsafe_allow_html=True)

# --- 3. PERSISTENT LOGIN CHECK ---
if 'logged_in' not in st.session_state:
    if "user" in st.query_params:
        st.session_state.logged_in = True
        st.session_state.user_type = st.query_params["type"]
        st.session_state.user_name = st.query_params["user"]
        st.session_state.client_id = st.query_params.get("id", "N/A")
    else:
        st.session_state.logged_in = False

# --- 4. MARKET HELPERS ---
@st.cache_data(ttl=60)
def get_ticker_data():
    indices = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN", "BANK NIFTY": "^NSEBANK"}
    vals = []
    for n, s in indices.items():
        try:
            p = yf.Ticker(s).history(period="1d")['Close'].iloc[-1]
            vals.append(f"{n}: {p:.2f}")
        except: continue
    return " | ".join(vals)

def get_market_status():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    # Market: Monday(0) to Friday(4), Time: 09:15 to 15:30
    if now.weekday() < 5:
        market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
        if market_start <= now <= market_end:
            return "🟢 MARKET OPEN"
    return "🔴 MARKET CLOSED"

# --- 5. APP VIEWS ---

def login_page():
    st.markdown(f'<div class="ticker-wrap"><div class="ticker">{get_ticker_data()}</div></div>', unsafe_allow_html=True)
    st.title("Anand Finserv")
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.container(border=True):
            mode = st.radio("Login as", ["Client", "Admin"], horizontal=True)
            name = st.text_input("Full Name")
            if mode == "Client":
                mob = st.text_input("Mobile Number")
                if st.button("Login to Dashboard"):
                    if name and len(mob) == 10:
                        cid = str(random.randint(100000, 999999))
                        st.session_state.logged_in, st.session_state.user_type, st.session_state.user_name, st.session_state.client_id = True, "Client", name, cid
                        st.query_params.user, st.query_params.type, st.query_params.id = name, "Client", cid
                        st.rerun()
            else:
                pwd = st.text_input("Admin Password", type="password")
                if st.button("Access Admin Panel"):
                    if pwd == "admin123":
                        st.session_state.logged_in, st.session_state.user_type, st.session_state.user_name = True, "Admin", "Administrator"
                        st.query_params.user, st.query_params.type = "Admin", "Admin"
                        st.rerun()

def admin_dashboard():
    st.header("🛡️ Admin Control Center")
    current_df = load_data()
    
    with st.sidebar:
        st.write(f"Logged in: {st.session_state.user_name}")
        if st.button("Logout"):
            st.query_params.clear()
            st.session_state.logged_in = False
            st.rerun()

    # Add New Level
    with st.expander("➕ Add New Trading Level", expanded=False):
        with st.form("add_form"):
            s = st.text_input("Stock (e.g. RELIANCE.NS)")
            t = st.selectbox("Type", ["BUY", "SELL"])
            e, tgt, sl = st.columns(3)
            ent_p = e.number_input("Entry")
            tgt_p = tgt.number_input("Target")
            sl_p = sl.number_input("Stop Loss")
            if st.form_submit_button("Publish to Google Sheet"):
                new_data = pd.DataFrame([{"id": random.randint(1000, 9999), "stock": s.upper(), "type": t, "entry": ent_p, "target": tgt_p, "sl": sl_p, "status": "Active", "exit_price": 0.0, "date": str(datetime.now().date())}])
                updated_df = pd.concat([current_df, new_data], ignore_index=True)
                save_to_sheet(updated_df)
                st.success("Level Published Successfully!")
                time.sleep(1)
                st.rerun()

    # Manage Levels
    st.subheader("Manage Active Levels")
    for i, row in current_df.iterrows():
        if row['status'] == "Active":
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                c1.write(f"**{row['stock']}** ({row['type']})")
                ex_p = c2.number_input("Exit Price", key=f"ex_{i}", value=float(row['target']))
                if c3.button("✅ Close", key=f"cl_{i}"):
                    current_df.at[i, 'status'], current_df.at[i, 'exit_price'] = "Closed", ex_p
                    save_to_sheet(current_df)
                    st.rerun()
                if c4.button("🗑️ Delete", key=f"dl_{i}"):
                    current_df.drop(i, inplace=True)
                    save_to_sheet(current_df)
                    st.rerun()

def client_dashboard():
    st.markdown(f'<div class="ticker-wrap"><div class="ticker">{get_ticker_data()}</div></div>', unsafe_allow_html=True)
    current_df = load_data()
    
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.caption(f"Client ID: #{st.session_state.get('client_id', 'N/A')}")
        st.write(get_market_status())
        if st.button("Logout"):
            st.query_params.clear()
            st.session_state.logged_in = False
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["⚡ Live Levels", "📜 History", "👤 Profile"])
    
    with tab1:
        active = current_df[current_df['status'] == "Active"]
        if active.empty: st.info("No active trades right now.")
        for _, l in active.iterrows():
            st.markdown(f"""
            <div class="stock-card">
                <h3>{l['stock']} <small>({l['type']})</small></h3>
                <p><b>Entry:</b> ₹{l['entry']} | <b>Target:</b> ₹{l['target']} | <b>SL:</b> <span style='color:red;'>₹{l['sl']}</span></p>
                <p style='font-size:0.8em; color:gray;'>📅 Date: {l['date']}</p>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        closed = current_df[current_df['status'] == "Closed"]
        if not closed.empty:
            st.dataframe(closed[["date", "stock", "type", "entry", "exit_price"]], use_container_width=True)
        else: st.info("No history yet.")

# --- MAIN ---
if st.session_state.logged_in:
    if st.session_state.user_type == "Admin": admin_dashboard()
    else: client_dashboard()
else:
    login_page()






