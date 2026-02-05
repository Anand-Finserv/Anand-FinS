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
# URL से टोकन चेक करना (ताकि रिफ्रेश पर लॉग इन रहे)
query_params = st.query_params

if "auth" in query_params and "logged_in" not in st.session_state:
    if query_params["auth"] == "admin_token":
        st.session_state.logged_in = True
        st.session_state.role = "Admin"
    elif query_params["auth"] == "client_token":
        st.session_state.logged_in = True
        st.session_state.role = "Client"

# --- FUNCTIONS ---

def get_live_indices():
    try:
        tickers = ['^NSEI', '^NSEBANK']
        data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
        n_price = data['^NSEI'].iloc[-1]
        n_prev = data['^NSEI'].iloc[0]
        b_price = data['^NSEBANK'].iloc[-1]
        b_prev = data['^NSEBANK'].iloc[0]
        return n_price, n_price-n_prev, b_price, b_price-b_prev
    except: return 0, 0, 0, 0

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

# --- LOGIN PAGE ---
def login_page():
    st.markdown("<h2 style='text-align: center;'>🔐 Anand Finserv Login</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin" and p == "anand123":
                    st.session_state.logged_in, st.session_state.role = True, "Admin"
                    st.query_params["auth"] = "admin_token" # URL में टोकन सेव करना
                    st.rerun()
                elif u == "client" and p == "client123":
                    st.session_state.logged_in, st.session_state.role = True, "Client"
                    st.query_params["auth"] = "client_token" # URL में टोकन सेव करना
                    st.rerun()
                else: st.error("Wrong ID/PW")

# --- DASHBOARDS ---
def admin_dashboard(df):
    st.title("👨‍💻 Admin Panel")
    if st.button("Logout"): 
        st.session_state.clear()
        st.query_params.clear() # URL टोकन साफ़ करना
        st.rerun()
    
    with st.form("new"):
        st.subheader("Add Call")
        c1, c2 = st.columns(2); s_name = c1.text_input("Stock Name"); c_type = c2.selectbox("Type", ["BUY", "SELL"])
        c3, c4, c5 = st.columns(3); ent, tgt, stl = c3.number_input("Entry"), c4.number_input("Target"), c5.number_input("SL")
        if st.form_submit_button("Publish"):
            new_row = pd.DataFrame([{"id": len(df)+1, "stock": s_name.upper(), "type": c_type, "entry": ent, "target": tgt, "sl": stl, "status": "Active", "exit_price": 0, "date": datetime.now().strftime("%Y-%m-%d")}])
            save_data(pd.concat([df, new_row], ignore_index=True)); st.rerun()
    
    st.subheader("Manage Records")
    edited = st.data_editor(df)
    if st.button("Save Changes"): save_data(edited); st.rerun()

def client_dashboard(df):
    n, nc, b, bc = get_live_indices()
    c1, c2 = st.columns(2); c1.metric("NIFTY 50", f"{n:.2f}", f"{nc:.2f}"); c2.metric("BANK NIFTY", f"{b:.2f}", f"{bc:.2f}")
    st.markdown("---")
    
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

    tab1, tab2 = st.tabs(["🚀 Live Calls", "📜 Past Performance"])
    with tab1:
        active = df[df['status'] == 'Active']
        if active.empty: st.info("No Active Calls")
        else:
            for i, r in active.iterrows():
                cp = get_cmp(r['stock']); color = "#00c853" if r['type'] == "BUY" else "#ff4b4b"
                st.markdown(f"<div style='border-left:5px solid {color}; background:#1e2130; padding:15px; border-radius:5px; margin-bottom:10px;'><h3>{r['stock']} ({r['type']})</h3><p>Entry: {r['entry']} | Target: {r['target']} | SL: {r['sl']}</p><h4 style='color:{color};'>CMP: {cp}</h4></div>", unsafe_allow_html=True)
    with tab2:
        past = df[df['status'] != 'Active']
        st.dataframe(past[['date', 'stock', 'type', 'status', 'entry', 'exit_price']], use_container_width=True)

# --- MAIN ENGINE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    data = load_data()
    run_auto_tracker(data)
    if st.session_state.role == "Admin": admin_dashboard(data)
    else: client_dashboard(data)
