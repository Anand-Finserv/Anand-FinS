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
# URL me token check karna taki refresh par logout na ho
query_params = st.query_params

if "auth" in query_params and "logged_in" not in st.session_state:
    if query_params["auth"] == "admin_secure":
        st.session_state.logged_in = True
        st.session_state.role = "Admin"
    elif query_params["auth"] == "client_secure":
        st.session_state.logged_in = True
        st.session_state.role = "Client"

# --- HELPER FUNCTIONS ---

def get_live_indices():
    """Nifty/BankNifty Header ke liye"""
    try:
        tickers = ['^NSEI', '^NSEBANK']
        data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
        n_p, b_p = data['^NSEI'].iloc[-1], data['^NSEBANK'].iloc[-1]
        n_o, b_o = data['^NSEI'].iloc[0], data['^NSEBANK'].iloc[0]
        return n_p, n_p-n_o, b_p, b_p-b_o
    except: return 0,0,0,0

def get_cmp(ticker):
    """Live Price lana"""
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
    """Target/SL Hit hone par auto-move karna"""
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

# --- 🔐 LOGIN PAGE ---
def login_page():
    st.markdown("<h2 style='text-align: center; color: #4CAF50;'>🔐 Anand Finserv Login</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.write("Please enter your credentials:")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            submitted = st.form_submit_button("Login")
            
            if submitted:
                # --- ADMIN CHECK ---
                if username == "admin" and password == "anand123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.query_params["auth"] = "admin_secure" # Token set
                    st.rerun()
                
                # --- CLIENT CHECK ---
                elif username == "client" and password == "client123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Client"
                    st.query_params["auth"] = "client_secure" # Token set
                    st.rerun()
                
                else:
                    st.error("❌ Incorrect Username or Password")

# --- DASHBOARDS ---

def client_dashboard(df):
    st.subheader("📡 Live Market Dashboard")
    
    # Live Indices
    n, nc, b, bc = get_live_indices()
    c1, c2 = st.columns(2)
    c1.metric("NIFTY 50", f"{n:.2f}", f"{nc:.2f}")
    c2.metric("BANK NIFTY", f"{b:.2f}", f"{bc:.2f}")
    st.markdown("---")
    
    # Logout Button
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

    # Tabs
    t1, t2 = st.tabs(["🚀 Active Calls", "📜 Past Performance"])
    
    with t1:
        active = df[df['status'] == 'Active']
        if active.empty: st.info("No Active Calls right now.")
        else:
            for i, r in active.iterrows():
                cp = get_cmp(r['stock'])
                color = "#00c853" if r['type'] == "BUY" else "#ff4b4b"
                st.markdown(f"""
                <div style='border-left:5px solid {color}; background:#1e2130; padding:15px; border-radius:5px; margin-bottom:10px;'>
                    <h3 style='margin:0;'>{r['stock']} ({r['type']})</h3>
                    <div style='display:flex; justify-content:space-between; margin-top:5px;'>
                        <span>Entry: {r['entry']}</span>
                        <span>Target: {r['target']}</span>
                    </div>
                    <div style='display:flex; justify-content:space-between; margin-top:5px;'>
                        <span>SL: <span style='color:#ff4b4b'>{r['sl']}</span></span>
                        <span>CMP: <b style='color:{color}; font-size:18px;'>{cp}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with t2:
        past = df[df['status'] != 'Active']
        if past.empty: st.info("No past history yet.")
        else:
            st.dataframe(past[['date', 'stock', 'type', 'status', 'entry', 'exit_price']], use_container_width=True)

def admin_dashboard(df):
    st.title("👨‍💻 Admin Panel")
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Add New
    with st.form("add_new"):
        st.subheader("📢 Publish New Call")
        c1, c2 = st.columns(2)
        s = c1.text_input("Stock Name")
        t = c2.selectbox("Type", ["BUY", "SELL"])
        c3, c4, c5 = st.columns(3)
        en, tg, sl = c3.number_input("Entry"), c4.number_input("Target"), c5.number_input("SL")
        
        if st.form_submit_button("Publish"):
            new_row = pd.DataFrame([{
                "id": len(df)+1, "stock": s.upper(), "type": t, "entry": en, 
                "target": tg, "sl": sl, "status": "Active", 
                "exit_price": 0, "date": datetime.now().strftime("%Y-%m-%d")
            }])
            save_data(pd.concat([df, new_row], ignore_index=True))
            st.success("Published!")
            st.rerun()

    # Manage Data
    st.subheader("📝 Manage Database")
    edited_df = st.data_editor(df, num_rows="dynamic")
    if st.button("💾 Save Changes"):
        save_data(edited_df)
        st.success("Database Updated!")
        st.rerun()

# --- MAIN ENGINE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
else:
    data = load_data()
    run_auto_tracker(data) # Auto Check
    if st.session_state.role == "Admin":
        admin_dashboard(data)
    else:
        client_dashboard(data)
