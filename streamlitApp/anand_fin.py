import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Anand Finserv AI", page_icon="📈", layout="centered")

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔄 PERSISTENT LOGIN LOGIC ---
query_params = st.query_params

if "auth" in query_params and "logged_in" not in st.session_state:
    if query_params["auth"] == "admin_token":
        st.session_state.logged_in = True
        st.session_state.role = "Admin"
    elif "client_token" in query_params["auth"]:
        st.session_state.logged_in = True
        st.session_state.role = "Client"
        # URL se naam wapas nikalna
        st.session_state.client_name = query_params.get("name", "Client")

# --- FUNCTIONS ---
def get_live_indices():
    try:
        tickers = ['^NSEI', '^NSEBANK']
        data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
        n_p, b_p = data['^NSEI'].iloc[-1], data['^NSEBANK'].iloc[-1]
        n_o, b_o = data['^NSEI'].iloc[0], data['^NSEBANK'].iloc[0]
        return n_p, n_p-n_o, b_p, b_p-b_o
    except: return 0,0,0,0

def get_cmp(ticker):
    try:
        stock = yf.Ticker(ticker + ".NS" if not ticker.endswith(".NS") else ticker)
        return round(stock.history(period="1d")['Close'].iloc[-1], 2)
    except: return 0.0

def load_data():
    try:
        data = conn.read(worksheet="Sheet1", ttl="2s")
        return data.fillna("")
    except: return pd.DataFrame(columns=['id', 'stock', 'type', 'entry', 'target', 'sl', 'status', 'exit_price', 'date'])

def save_data(df):
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()
        return True
    except: return False

# --- LOGIN PAGE ---
def login_page():
    st.markdown("<h2 style='text-align: center;'>🔐 Anand Finserv Terminal</h2>", unsafe_allow_html=True)
    
    tab_client, tab_admin = st.tabs(["👤 Client Login", "🛠️ Admin Access"])
    
    with tab_client:
        with st.form("client_login"):
            full_name = st.text_input("Enter Full Name")
            mobile = st.text_input("Enter Mobile Number", max_chars=10)
            if st.form_submit_button("Access Dashboard"):
                if len(mobile) == 10 and full_name:
                    st.session_state.logged_in = True
                    st.session_state.role = "Client"
                    st.session_state.client_name = full_name
                    # URL tokens
                    st.query_params["auth"] = f"client_token_{mobile}"
                    st.query_params["name"] = full_name
                    st.rerun()
                else:
                    st.error("Please enter a valid 10-digit mobile number and name.")

    with tab_admin:
        with st.form("admin_login"):
            u = st.text_input("Admin ID")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Admin Login"):
                if u == "admin" and p == "anand123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.query_params["auth"] = "admin_token"
                    st.rerun()
                else: st.error("Invalid Admin Credentials")

# --- DASHBOARDS ---
def client_dashboard(df):
    # Welcome Message
    name = st.session_state.get('client_name', 'Client')
    st.subheader(f"Welcome, {name}! 👋")
    
    n, nc, b, bc = get_live_indices()
    col1, col2 = st.columns(2)
    col1.metric("NIFTY 50", f"{n:.2f}", f"{nc:.2f}")
    col2.metric("BANK NIFTY", f"{b:.2f}", f"{bc:.2f}")
    
    st.markdown("---")
    
    t1, t2 = st.tabs(["🚀 Active Calls", "📜 Performance History"])
    with t1:
        active = df[df['status'] == 'Active']
        if active.empty: st.info("No active calls available.")
        else:
            for i, r in active.iterrows():
                cp = get_cmp(r['stock'])
                color = "#00c853" if r['type'] == "BUY" else "#ff4b4b"
                st.markdown(f"<div style='border-left:5px solid {color}; background:#1e2130; padding:15px; border-radius:5px; margin-bottom:10px;'><h3>{r['stock']} ({r['type']})</h3><p>Entry: {r['entry']} | Target: {r['target']} | SL: {r['sl']}</p><h4 style='color:{color};'>CMP: {cp}</h4></div>", unsafe_allow_html=True)
    
    with t2:
        past = df[df['status'] != 'Active']
        st.dataframe(past[['date', 'stock', 'type', 'status', 'entry', 'exit_price']], use_container_width=True)

    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

# --- ADMIN PANEL (Same as before) ---
def admin_dashboard(df):
    st.title("👨‍💻 Admin Control Panel")
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    # (Admin form logic...)
    with st.form("add"):
        c1, c2 = st.columns(2); s_name = c1.text_input("Stock Symbol"); c_type = c2.selectbox("Type", ["BUY", "SELL"])
        c3, c4, c5 = st.columns(3); ent, tgt, stl = c3.number_input("Entry"), c4.number_input("Target"), c5.number_input("SL")
        if st.form_submit_button("Publish"):
            new_row = pd.DataFrame([{"id": len(df)+1, "stock": s_name.upper(), "type": c_type, "entry": ent, "target": tgt, "sl": stl, "status": "Active", "exit_price": 0, "date": datetime.now().strftime("%Y-%m-%d")}])
            save_data(pd.concat([df, new_row], ignore_index=True)); st.rerun()
    st.data_editor(df)

# --- ENGINE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    data = load_data()
    if st.session_state.role == "Admin": admin_dashboard(data)
    else: client_dashboard(data)

