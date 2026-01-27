import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import time

# --- PAGE CONFIG ---
st.set_page_config(page_title="Anand Finserv Pro", page_icon="📈", layout="centered")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .login-box { padding: 20px; border-radius: 10px; background-color: #262730; margin-top: 50px; }
    .card { padding: 15px; border-radius: 10px; margin-bottom: 15px; background-color: #1e2130; }
    .buy-card { border-left: 5px solid #00c853; }
    .sell-card { border-left: 5px solid #ff4b4b; }
    </style>
""", unsafe_allow_html=True)

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIONS ---

def get_cmp(ticker):
    """Yahoo Finance se Live Price lata hai"""
    try:
        # Agar .NS nahi laga hai to laga do
        if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
            ticker = ticker + ".NS"
        
        stock = yf.Ticker(ticker)
        # Fast fetch ke liye 'fast_info' ya last history
        price = stock.history(period="1d")['Close'].iloc[-1]
        return round(price, 2)
    except:
        return 0.0

def load_data():
    """Sheet se data read karta hai"""
    try:
        data = conn.read(worksheet="Sheet1", ttl="5s")
        # Null values ko empty string bana do taaki error na aaye
        return data.fillna("")
    except:
        # Agar connection fail ho ya sheet khali ho, to Empty DataFrame bhejo (Fake data nahi)
        return pd.DataFrame(columns=['id', 'stock', 'type', 'entry', 'target', 'sl', 'status'])

def save_data(df):
    """Sheet me data save karta hai"""
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

# --- PAGES ---

def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Anand Finserv Login</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                # ADMIN LOGIN
                if username == "admin" and password == "anand123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.rerun()
                
                # CLIENT LOGIN
                elif username == "client" and password == "client123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Client"
                    st.rerun()
                
                else:
                    st.error("Invalid Username or Password")

def admin_dashboard():
    st.title("👨‍💻 Admin Panel")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    st.markdown("---")
    
    # 1. ADD NEW CALL
    st.subheader("📢 Publish New Call")
    with st.form("new_call"):
        c1, c2 = st.columns(2)
        stock_name = c1.text_input("Stock Symbol (e.g. RELIANCE)")
        call_type = c2.selectbox("Type", ["BUY", "SELL"])
        
        c3, c4, c5 = st.columns(3)
        entry = c3.number_input("Entry Price", min_value=0.0)
        target = c4.number_input("Target", min_value=0.0)
        sl = c5.number_input("Stop Loss", min_value=0.0)
        
        if st.form_submit_button("Publish"):
            df = load_data()
            new_id = len(df) + 1
            new_row = pd.DataFrame([{
                "id": new_id,
                "stock": stock_name.upper(),
                "type": call_type,
                "entry": entry,
                "target": target,
                "sl": sl,
                "status": "Active"
            }])
            
            # Agar purana data hai to usme jodo, nahi to naya banao
            if not df.empty:
                updated_df = pd.concat([df, new_row], ignore_index=True)
            else:
                updated_df = new_row
                
            save_data(updated_df)
            st.success(f"{stock_name} Added!")
            st.rerun()

    # 2. MANAGE LEVELS
    st.markdown("---")
    st.subheader("📋 Manage Active Levels")
    df = load_data()
    
    if not df.empty:
        edited_df = st.data_editor(df, num_rows="dynamic")
        if st.button("💾 Save Changes"):
            save_data(edited_df)
            st.success("Database Updated!")
    else:
        st.info("No data in sheet.")

def client_dashboard():
    st.title("📡 Live Calls Dashboard")
    
    col_btn, col_logout = st.columns([4, 1])
    with col_btn:
        if st.button("🔄 Refresh Prices"):
            st.rerun()
    with col_logout:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    st.markdown("---")
    
    df = load_data()
    
    # Check if data exists
    if df.empty:
        st.info("📭 No Active Calls Available.")
        return

    # Filter Active Calls
    if 'status' in df.columns:
        active_calls = df[df['status'] == 'Active']
    else:
        active_calls = df # Agar status column nahi hai to sab dikhao

    if active_calls.empty:
        st.info("📭 No Active Calls Today.")
    else:
        # Cards Display Loop
        for index, row in active_calls.iterrows():
            # Get Live CMP
            cmp = get_cmp(row['stock'])
            
            # Color Logic
            card_class = "buy-card" if row['type'] == "BUY" else "sell-card"
            text_color = "#00e676" if row['type'] == "BUY" else "#ff5252"
            
            # P/L Calculation (Rough)
            pl_color = "white"
            if cmp > 0:
                if row['type'] == "BUY":
                    pl_color = "#00e676" if cmp > row['entry'] else "#ff5252"
                else: # SELL
                    pl_color = "#00e676" if cmp < row['entry'] else "#ff5252"

            # HTML Card
            st.markdown(f"""
            <div class="card {card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h2 style="margin:0;">{row['stock']}</h2>
                    <h3 style="margin:0; color:{text_color};">{row['type']}</h3>
                </div>
                <hr style="border-color: #333;">
                <div style="display:flex; justify-content:space-between; font-size: 18px;">
                    <span>Entry: <b>{row['entry']}</b></span>
                    <span>Target: <b>{row['target']}</b></span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size: 18px; margin-top:5px;">
                    <span>SL: <span style="color:#ff5252;">{row['sl']}</span></span>
                    <span>CMP: <b style="color:{pl_color}; font-size: 22px;">{cmp}</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- MAIN LOGIC ---

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    if st.session_state.role == "Admin":
        admin_dashboard()
    else:
        client_dashboard()
else:
    login_page()



