import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Anand Finserv Auto", page_icon="📈", layout="centered")

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIONS ---

def get_cmp(ticker):
    try:
        if not ticker.endswith(".NS"): ticker = ticker + ".NS"
        stock = yf.Ticker(ticker)
        return round(stock.history(period="1d")['Close'].iloc[-1], 2)
    except:
        return 0.0

def load_data():
    try:
        data = conn.read(worksheet="Sheet1", ttl="2s") # Fast refresh
        return data.fillna("")
    except:
        return pd.DataFrame(columns=['id', 'stock', 'type', 'entry', 'target', 'sl', 'status', 'exit_price', 'date'])

def save_data(df):
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()
        return True
    except:
        return False

# --- 🤖 AUTOMATIC SYSTEM LOGIC ---
def run_auto_tracker(df):
    """Yeh function check karega ki Target ya SL hit hua ya nahi"""
    updated = False
    
    for index, row in df.iterrows():
        if row['status'] == 'Active':
            current_price = get_cmp(row['stock'])
            if current_price == 0: continue
            
            target = float(row['target'])
            sl = float(row['sl'])
            
            # BUY Order Logic
            if row['type'] == "BUY":
                if current_price >= target:
                    df.at[index, 'status'] = 'Target Hit ✅'
                    df.at[index, 'exit_price'] = current_price
                    updated = True
                elif current_price <= sl:
                    df.at[index, 'status'] = 'SL Hit ❌'
                    df.at[index, 'exit_price'] = current_price
                    updated = True
            
            # SELL Order Logic
            elif row['type'] == "SELL":
                if current_price <= target:
                    df.at[index, 'status'] = 'Target Hit ✅'
                    df.at[index, 'exit_price'] = current_price
                    updated = True
                elif current_price >= sl:
                    df.at[index, 'status'] = 'SL Hit ❌'
                    df.at[index, 'exit_price'] = current_price
                    updated = True
    
    if updated:
        save_data(df)
        st.rerun()

# --- MAIN APP ---

# 1. Data Load karein
df = load_data()

# 2. Auto Tracker chalayein (Background check)
if not df.empty:
    run_auto_tracker(df)

# --- UI TABS ---
st.title("Anand Finserv Pro")
tab1, tab2 = st.tabs(["🚀 Live Calls", "📜 Past Performance"])

with tab1:
    active = df[df['status'] == 'Active']
    if active.empty:
        st.info("No Active Calls")
    else:
        for idx, row in active.iterrows():
            st.write(f"**{row['stock']}** | CMP: {get_cmp(row['stock'])} | Target: {row['target']}")

with tab2:
    # Jo active nahi hain wo yahan dikhenge
    past = df[df['status'] != 'Active']
    st.table(past[['date', 'stock', 'type', 'status', 'entry', 'exit_price']])

# (Login & Admin logic purane code jaisi hi rahegi) # Divider line

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







