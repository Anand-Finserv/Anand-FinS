import streamlit as st
import pandas as pd
import yfinance as yf
import random
import time
from datetime import datetime
import pytz

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & SESSION STATE SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Anand Finserv", page_icon="📈", layout="wide")

# Initialize Session State Variables (Database & User Info)
if 'levels_db' not in st.session_state:
    # Dummy data for testing
    st.session_state.levels_db = [
        {"id": 101, "stock": "TATAMOTORS.NS", "type": "BUY", "entry": 980.0, "target": 1050.0, "sl": 960.0, "status": "Active", "exit_price": 0.0, "date": "2024-01-01"},
        {"id": 102, "stock": "RELIANCE.NS", "type": "BUY", "entry": 2400.0, "target": 2500.0, "sl": 2350.0, "status": "Closed", "exit_price": 2480.0, "date": "2024-01-02"}
    ]

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_type' not in st.session_state: st.session_state.user_type = "Client" # Client or Admin
if 'client_id' not in st.session_state: st.session_state.client_id = None
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'user_mobile' not in st.session_state: st.session_state.user_mobile = ""

# -----------------------------------------------------------------------------
# 2. CSS STYLING (Professional Blue Theme)
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    /* Global Background */
    [data-testid="stAppViewContainer"] { background-color: #f0f2f6; }
    
    /* Blue Buttons */
    .stButton>button {
        background-color: #007bff; color: white; border-radius: 6px;
        border: none; padding: 0.5rem 1rem; font-weight: 600; width: 100%;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #0056b3; color: white; border: none; }
    
    /* Red Delete Button override */
    div[data-testid="stVerticalBlock"] > div > div > div > div > .delete-btn > button {
        background-color: #dc3545 !important;
    }

    /* Card Styling */
    .stock-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff;
        margin-bottom: 15px;
    }
    
    /* Market Ticker */
    .ticker-wrap {
        width: 100%; overflow: hidden; background: #111827; color: white;
        padding: 8px 0; font-family: sans-serif; margin-bottom: 20px;
    }
    .ticker { display: flex; white-space: nowrap; animation: marquee 30s linear infinite; }
    @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    
    /* Status Colors */
    .profit { color: #198754; font-weight: bold; }
    .loss { color: #dc3545; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def get_market_status():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    # Market Open: Mon-Fri, 09:15 to 15:30
    if now.weekday() < 5:
        start = now.replace(hour=9, minute=15, second=0)
        end = now.replace(hour=15, minute=30, second=0)
        if start <= now <= end:
            return "🟢 Market Open"
    return "🔴 Market Closed"

@st.cache_data(ttl=60)
def fetch_indices():
    indices = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN", "BANK NIFTY": "^NSEBANK"}
    ticker_html = []
    for name, symbol in indices.items():
        try:
            data = yf.Ticker(symbol).history(period="1d")
            if not data.empty:
                price = data['Close'].iloc[-1]
                change = price - data['Open'].iloc[-1]
                color = "#4ade80" if change >= 0 else "#f87171" # Green or Red
                sign = "+" if change >= 0 else ""
                ticker_html.append(f"{name}: <span style='color:{color}'>{price:.0f} ({sign}{change:.1f})</span>")
        except:
            continue
    return " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(ticker_html)

@st.cache_data(ttl=30)
def get_live_price(ticker_symbol):
    try:
        data = yf.Ticker(ticker_symbol).history(period="1d")
        if not data.empty:
            return round(data['Close'].iloc[-1], 2)
    except:
        return None
    return None

def calculate_pnl(call_type, entry, current):
    if call_type == "BUY": return round(current - entry, 2)
    else: return round(entry - current, 2)

# -----------------------------------------------------------------------------
# 4. VIEWS (LOGIN, CLIENT, ADMIN)
# -----------------------------------------------------------------------------

def login_page():
    # Scrolling Ticker on Login Page too
    st.markdown(f"""<div class="ticker-wrap"><div class="ticker">{fetch_indices()}</div></div>""", unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; color: #007bff;'>Anand Finserv </h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.container(border=True):
            login_mode = st.radio("Login Type", ["Client", "Admin"], horizontal=True)
            
            if login_mode == "Client":
                name = st.text_input("Full Name")
                mobile = st.text_input("Mobile Number (10 digits)")
                if st.button("🚀 Client Login"):
                    if name and len(mobile) == 10 and mobile.isdigit():
                        st.session_state.logged_in = True
                        st.session_state.user_type = "Client"
                        st.session_state.user_name = name
                        st.session_state.user_mobile = mobile
                        if not st.session_state.client_id:
                            st.session_state.client_id = random.randint(100000, 999999)
                        st.rerun()
                    else:
                        st.error("Enter valid Name and Mobile Number")
            
            else: # Admin Login
                password = st.text_input("Password", type="password")
                if st.button("🔐 Admin Login"):
                    if password == "admin7232": # Change this password!
                        st.session_state.logged_in = True
                        st.session_state.user_type = "Admin"
                        st.session_state.user_name = "Administrator"
                        st.rerun()
                    else:
                        st.error("Invalid Password")

def client_dashboard():
    # Ticker
    st.markdown(f"""<div class="ticker-wrap"><div class="ticker">{fetch_indices()}</div></div>""", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/user-male-circle--v1.png", width=80)
        st.title(f"{st.session_state.user_name}")
        st.caption(f"ID: #{st.session_state.client_id}")
        st.markdown(f"**Status:** {get_market_status()}")
        st.markdown("---")
        if st.button("Logout", type="primary"):
            st.session_state.logged_in = False
            st.rerun()

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Dashboard", "📜 History", "📰 News", "👤 Profile"])

    # --- TAB 1: ACTIVE DASHBOARD ---
    with tab1:
        st.subheader("Live Recommendations")
        if st.button("🔄 Refresh Prices"): st.rerun()
        
        active_levels = [l for l in st.session_state.levels_db if l['status'] == "Active"]
        
        if not active_levels:
            st.info("No active trades at the moment.")
        
        for l in active_levels:
            # Try to fetch live price
            cmp = get_live_price(l['stock'])
            
            # If yfinance fails, show N/A
            display_cmp = cmp if cmp else "Loading..."
            pnl_text = "N/A"
            pnl_color = "black"
            
            if cmp:
                pnl = calculate_pnl(l['type'], l['entry'], cmp)
                pnl_color = "green" if pnl >= 0 else "red"
                pnl_text = f"₹ {pnl}"

            st.markdown(f"""
            <div class="stock-card">
                <div style="display:flex; justify-content:space-between;">
                    <h3 style="margin:0;">{l['stock']} <span style="font-size:0.6em; background:#e0e7ff; color:#007bff; padding:2px 6px; border-radius:4px;">{l['type']}</span></h3>
                    <h3 style="margin:0; color:{pnl_color};">{pnl_text}</h3>
                </div>
                <hr style="margin: 10px 0;">
                <div style="display:flex; justify-content:space-between; font-weight:500;">
                    <span>Entry: ₹{l['entry']}</span>
                    <span>CMP: ₹{display_cmp}</span>
                    <span>Target: ₹{l['target']}</span>
                    <span style="color:red;">SL: ₹{l['sl']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # --- TAB 2: HISTORY (CLOSED TRADES) ---
    with tab2:
        st.subheader("Performance History")
        closed_levels = [l for l in st.session_state.levels_db if l['status'] == "Closed"]
        
        if closed_levels:
            data = []
            total_pnl = 0
            for l in closed_levels:
                profit = calculate_pnl(l['type'], l['entry'], l['exit_price'])
                total_pnl += profit
                data.append({
                    "Stock": l['stock'],
                    "Type": l['type'],
                    "Entry": l['entry'],
                    "Exit Price": l['exit_price'],
                    "P&L": profit,
                    "Date": l['date']
                })
            
            st.metric("Total Realized P&L", f"₹ {total_pnl:,.2f}")
            
            df = pd.DataFrame(data)
            # Styling the dataframe
            st.dataframe(
                df.style.map(lambda x: 'color: green' if x > 0 else 'color: red', subset=['P&L'])
                .format({"Entry": "{:.2f}", "Exit Price": "{:.2f}", "P&L": "{:.2f}"}),
                use_container_width=True
            )
        else:
            st.info("No closed trades history found.")

    # --- TAB 3: NEWS ---
    with tab3:
        st.header("Market News")
        try:
            news = yf.Ticker("^NSEI").news
            for item in news[:5]:
                st.markdown(f"**{item['title']}**")
                st.caption(f"Source: {item['publisher']}")
                st.markdown(f"[Read Article]({item['link']})")
                st.markdown("---")
        except:
            st.warning("Could not load news. Check internet connection.")

    # --- TAB 4: PROFILE ---
    with tab4:
        st.subheader("My Account")
        st.write(f"**Name:** {st.session_state.user_name}")
        st.write(f"**Client ID:** {st.session_state.client_id}")
        st.write(f"**Mobile:** +91 {st.session_state.user_mobile}")
        st.success("Account Status: Active ✅")

def admin_dashboard():
    # Sidebar
    with st.sidebar:
        st.title("Admin Panel")
        st.error("Mode: Administrator")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("💼 Admin Control Center")
    
    # 1. ADD NEW LEVEL SECTION
    with st.expander("➕ Add New Level", expanded=True):
        with st.form("new_trade"):
            c1, c2, c3 = st.columns(3)
            stock = c1.text_input("Stock Symbol (e.g. TATAMOTORS.NS)")
            call_type = c2.selectbox("Type", ["BUY", "SELL"])
            entry = c3.number_input("Entry Price", min_value=0.0, step=0.1)
            
            c4, c5 = st.columns(2)
            target = c4.number_input("Target", min_value=0.0, step=0.1)
            sl = c5.number_input("Stop Loss", min_value=0.0, step=0.1)
            
            if st.form_submit_button("Publish Trade"):
                if stock and entry > 0:
                    new_id = random.randint(1000, 9999)
                    new_trade = {
                        "id": new_id,
                        "stock": stock.upper(),
                        "type": call_type,
                        "entry": entry,
                        "target": target,
                        "sl": sl,
                        "status": "Active",
                        "exit_price": 0.0,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                    st.session_state.levels_db.insert(0, new_trade)
                    st.success(f"Published {stock} successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please enter valid Stock Name and Entry Price")

    # 2. MANAGE ACTIVE TRADES
    st.subheader("⚡ Manage Active Trades")
    
    active_indices = [i for i, l in enumerate(st.session_state.levels_db) if l['status'] == "Active"]
    
    if not active_indices:
        st.info("No active trades running.")
    
    for idx in active_indices:
        trade = st.session_state.levels_db[idx]
        
        with st.container(border=True):
            cols = st.columns([3, 2, 2, 2])
            
            # Display Info
            cols[0].markdown(f"**{trade['stock']}** ({trade['type']})")
            cols[0].caption(f"Entry: {trade['entry']} | SL: {trade['sl']}")
            
            # Input for Exit Price
            exit_val = cols[1].number_input("Exit Price", key=f"ex_{trade['id']}", value=float(trade['target']))
            
            # BUTTON 1: CLOSE (Saves to History)
            if cols[2].button("✅ Close", key=f"cls_{trade['id']}"):
                st.session_state.levels_db[idx]['status'] = "Closed"
                st.session_state.levels_db[idx]['exit_price'] = exit_val
                st.success(f"Trade Closed @ {exit_val}. Saved to History.")
                time.sleep(1)
                st.rerun()

            # BUTTON 2: DELETE (Removes completely - NO History)
            if cols[3].button("🗑️ Delete", key=f"del_{trade['id']}"):
                # Remove from list completely
                st.session_state.levels_db.pop(idx)
                st.warning("Trade Deleted permanently (Not saved in history).")
                time.sleep(1)
                st.rerun()

# -----------------------------------------------------------------------------
# 5. MAIN APP EXECUTION
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    if st.session_state.logged_in:
        if st.session_state.user_type == "Admin":
            admin_dashboard()
        else:
            client_dashboard()
    else:
        login_page()