import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Anand Finserv Pro", page_icon="📈", layout="centered")

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 🔄 STAY LOGGED IN LOGIC ---
query_params = st.query_params

if "auth" in query_params and "logged_in" not in st.session_state:
    if query_params["auth"] == "admin_secure":
        st.session_state.logged_in = True
        st.session_state.role = "Admin"
    elif query_params["auth"] == "client_secure":
        st.session_state.logged_in = True
        st.session_state.role = "Client"

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
        if not ticker.endswith(".NS"): ticker = ticker + ".NS"
        stock = yf.Ticker(ticker)
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

def run_auto_tracker(df):
    updated = False
    for index, row in df.iterrows():
        if row['status'] == 'Active':
            cp = get_cmp(row['stock'])
            if cp == 0: continue
            t, s = float(row['target']), float(row['sl'])
            if row['type'] == "BUY":
                if cp >= t: df.at[index, 'status'], df.at[index, 'exit_price'], updated = 'Target Hit ✅', cp, True
                elif cp <= s: df.at[index, 'status'], df.at[index, 'exit_price'], updated = 'SL Hit ❌', cp, True
            elif row['type'] == "SELL":
                if cp <= t: df.at[index, 'status'], df.at[index, 'exit_price'], updated = 'Target Hit ✅', cp, True
                elif cp >= s: df.at[index, 'status'], df.at[index, 'exit_price'], updated = 'SL Hit ❌', cp, True
    if updated:
        save_data(df)
        st.rerun()

# --- 🔐 NEW LOGIN PAGE (SEPARATE TABS) ---
def login_page():
    st.markdown("<h2 style='text-align: center;'>🔐 Anand Finserv App</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # DO ALAG TABS BANA DIYE HAIN
    tab_client, tab_admin = st.tabs(["👤 Client Login", "👨‍💻 Admin Login"])
    
    # 1. CLIENT LOGIN TAB
    with tab_client:
        st.info("Clients log in here 👇")
        with st.form("client_form"):
            u = st.text_input("Client ID")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login as Client"):
                if u == "client" and p == "client123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Client"
                    st.query_params["auth"] = "client_secure"
                    st.rerun()
                else:
                    st.error("Wrong Client ID or Password")

    # 2. ADMIN LOGIN TAB
    with tab_admin:
        st.warning("Only for Owner/Admin 👇")
        with st.form("admin_form"):
            u = st.text_input("Admin ID")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login as Admin"):
                if u == "admin" and p == "anand123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.query_params["auth"] = "admin_secure"
                    st.rerun()
                else:
                    st.error("Wrong Admin Credentials")

# --- DASHBOARDS ---
def client_dashboard(df):
    n, nc, b, bc = get_live_indices()
    c1, c2 = st.columns(2)
    c1.metric("NIFTY 50", f"{n:.2f}", f"{nc:.2f}")
    c2.metric("BANK NIFTY", f"{b:.2f}", f"{bc:.2f}")
    st.markdown("---")
    
    if st.button("🚪 Logout Client"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

    t1, t2 = st.tabs(["🚀 Active Calls", "📜 Past Performance"])
    with t1:
        active = df[df['status'] == 'Active']
        if active.empty: st.info("No Active Calls")
        else:
            for i, r in active.iterrows():
                cp = get_cmp(r['stock'])
                color = "#00c853" if r['type'] == "BUY" else "#ff4b4b"
                st.markdown(f"<div style='border-left:5px solid {color}; background:#1e2130; padding:15px; border-radius:5px; margin-bottom:10px;'><h3>{r['stock']} ({r['type']})</h3><p>Entry: {r['entry']} | Target: {r['target']} | SL: {r['sl']}</p><h4 style='color:{color};'>CMP: {cp}</h4></div>", unsafe_allow_html=True)
    with t2:
        past = df[df['status'] != 'Active']
        st.dataframe(past[['date', 'stock', 'type', 'status', 'entry', 'exit_price']], use_container_width=True)

def admin_dashboard(df):
    st.title("👨‍💻 Admin Panel")
    if st.button("🚪 Logout Admin"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    
    with st.form("add"):
        st.subheader("Add Call")
        c1, c2 = st.columns(2); s=c1.text_input("Stock"); t=c2.selectbox("Type",["BUY","SELL"])
        c3, c4, c5 = st.columns(3); en=c3.number_input("Entry"); tg=c4.number_input("Target"); sl=c5.number_input("SL")
        if st.form_submit_button("Publish"):
            row = pd.DataFrame([{"id":len(df)+1,"stock":s.upper(),"type":t,"entry":en,"target":tg,"sl":sl,"status":"Active","exit_price":0,"date":datetime.now().strftime("%Y-%m-%d")}])
            save_data(pd.concat([df, row], ignore_index=True)); st.rerun()
    
    st.subheader("Manage Data")
    edited = st.data_editor(df, num_rows="dynamic")
    if st.button("Save Changes"): save_data(edited); st.rerun()

# --- ENGINE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    data = load_data()
    run_auto_tracker(data)
    if st.session_state.role == "Admin": admin_dashboard(data)
    else: client_dashboard(data)
