import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- PAGE CONFIG ---
st.set_page_config(page_title="Anand Finserv Live", page_icon="📈", layout="centered")

# --- CUSTOM CSS FOR FLOATING INDEX ---
st.markdown("""
    <style>
    .metric-container {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIONS ---

def get_live_indices():
    """Nifty aur BankNifty ka live data laata hai"""
    try:
        # Nifty 50 (^NSEI) and Bank Nifty (^NSEBANK)
        tickers = ['^NSEI', '^NSEBANK']
        data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
        
        # Latest price nikalna
        nifty_price = data['^NSEI'].iloc[-1]
        nifty_open = data['^NSEI'].iloc[0]
        nifty_change = nifty_price - nifty_open
        
        bank_price = data['^NSEBANK'].iloc[-1]
        bank_open = data['^NSEBANK'].iloc[0]
        bank_change = bank_price - bank_open
        
        return nifty_price, nifty_change, bank_price, bank_change
    except Exception as e:
        return 0, 0, 0, 0

def load_data():
    try:
        data = conn.read(worksheet="Sheet1", ttl="5s")
        return data.fillna("")
    except:
        return pd.DataFrame(columns=['id', 'stock', 'type', 'entry', 'target', 'sl', 'status', 'exit_price', 'date'])

def save_data(df):
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

# --- LIVE INDICES DISPLAY (TOP HEADER) ---
st.title("📈 Anand Finserv Live")

# Data fetch karna
nifty, n_change, bank, b_change = get_live_indices()

# Top par indices dikhana (Floating look)
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="NIFTY 50", value=f"{nifty:.2f}", delta=f"{n_change:.2f}")
    with col2:
        st.metric(label="BANK NIFTY", value=f"{bank:.2f}", delta=f"{b_change:.2f}")

st.markdown("---") # Divider line

# --- LOGIN & DASHBOARD ---

# Sidebar for Login
st.sidebar.header("🔐 Login Panel")
user_type = st.sidebar.radio("Select Role", ["Client", "Admin"])

if user_type == "Admin":
    st.sidebar.markdown("---")
    password = st.sidebar.text_input("Admin Password", type="password")
    
    if password == "anand123":  
        st.header("👨‍💻 Admin Panel")
        
        # Add New Level Form
        with st.form("add_level"):
            st.subheader("Add New Call")
            col1, col2 = st.columns(2)
            stock = col1.text_input("Stock Name (e.g. RELIANCE)")
            call_type = col2.selectbox("Type", ["BUY", "SELL"])
            
            c1, c2, c3 = st.columns(3)
            entry = c1.number_input("Entry Price")
            target = c2.number_input("Target")
            sl = c3.number_input("Stop Loss")
            
            if st.form_submit_button("🚀 Publish Level"):
                df = load_data()
                new_id = len(df) + 1
                new_row = pd.DataFrame([{
                    "id": new_id, "stock": stock.upper(), "type": call_type,
                    "entry": entry, "target": target, "sl": sl,
                    "status": "Active", "exit_price": 0.0, "date": datetime.now().strftime("%Y-%m-%d")
                }])
                save_data(pd.concat([df, new_row], ignore_index=True))
                st.success(f"{stock} Added!")
                st.rerun()
        
        # Manage Existing Levels
        st.subheader("📋 Manage Levels")
        df = load_data()
        if not df.empty:
            edited_df = st.data_editor(df, num_rows="dynamic")
            if st.button("💾 Update Changes"):
                save_data(edited_df)
                st.success("Updated!")

    elif password:
        st.sidebar.error("Wrong Password")

else:
    # --- CLIENT DASHBOARD ---
    st.header("📡 Live Calls Dashboard")
    
    if st.button("🔄 Refresh Market Data"):
        st.rerun()
    
    df = load_data()
    
    if not df.empty and 'status' in df.columns:
        active_calls = df[df['status'] == 'Active']
        if not active_calls.empty:
            for index, row in active_calls.iterrows():
                card_color = "#00C853" if row['type'] == "BUY" else "#FF5252" # Green/Red Hex codes
                
                st.markdown(f"""
                <div style="border-left: 5px solid {card_color}; background-color: #262730; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
                    <h3 style="margin: 0;">{row['stock']} <span style="color: {card_color}; font-size: 20px;">({row['type']})</span></h3>
                    <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                        <span>🚀 Entry: <b>{row['entry']}</b></span>
                        <span>🎯 Target: <b>{row['target']}</b></span>
                        <span>🛑 SL: <b>{row['sl']}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("✅ No Active Calls.")
    else:
        st.warning("Loading data...")






