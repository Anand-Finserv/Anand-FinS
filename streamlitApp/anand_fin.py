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
    .card { padding: 15px; border-radius: 10px; margin-bottom: 15px; background-color: #1e2130; }
    .buy-card { border-left: 5px solid #00c853; }
    .sell-card { border-left: 5px solid #ff4b4b; }
    
    /* Table Styling */
    .stDataFrame { border: 1px solid #333; }
    </style>
""", unsafe_allow_html=True)

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCTIONS ---

def get_cmp(ticker):
    """Yahoo Finance se Live Price lata hai"""
    try:
        if not ticker.endswith(".NS") and not ticker.endswith(".BO"):
            ticker = ticker + ".NS"
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'].iloc[-1]
        return round(price, 2)
    except:
        return 0.0

def load_data():
    """Sheet se data read karta hai"""
    try:
        data = conn.read(worksheet="Sheet1", ttl="5s")
        return data.fillna("")
    except:
        return pd.DataFrame(columns=['id', 'stock', 'type', 'entry', 'target', 'sl', 'status', 'exit_price', 'date'])

def save_data(df):
    """Sheet me data save karta hai"""
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

def calculate_pnl(row):
    """Profit/Loss Points calculate karta hai"""
    try:
        entry = float(row['entry'])
        exit_p = float(row['exit_price'])
        
        if exit_p == 0: return 0  # Agar exit price nahi dala to 0
        
        if row['type'] == "BUY":
            return round(exit_p - entry, 2)
        else: # SELL
            return round(entry - exit_p, 2)
    except:
        return 0

# --- PAGES ---

def login_page():
    st.markdown("<h1 style='text-align: center; color: #4CAF50;'>🔐 Anand Finserv Login</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login Securely")
            
            if submitted:
                if username == "admin" and password == "anand123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.rerun()
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
        
        if st.form_submit_button("Publish Call"):
            df = load_data()
            new_id = len(df) + 1
            today_date = pd.Timestamp.now().strftime("%Y-%m-%d")
            
            new_row = pd.DataFrame([{
                "id": new_id,
                "stock": stock_name.upper(),
                "type": call_type,
                "entry": entry,
                "target": target,
                "sl": sl,
                "status": "Active",
                "exit_price": 0.0,
                "date": today_date
            }])
            
            if not df.empty:
                updated_df = pd.concat([df, new_row], ignore_index=True)
            else:
                updated_df = new_row
                
            save_data(updated_df)
            st.success(f"{stock_name} Added!")
            st.rerun()

    # 2. MANAGE LEVELS (Edit / Close Trade)
    st.markdown("---")
    st.subheader("📋 Manage Active Levels (Close Trades Here)")
    st.info("💡 To Close a trade: Change Status to 'Target Hit'/'SL Hit' AND enter Exit Price.")
    
    df = load_data()
    if not df.empty:
        # User can edit table directly
        edited_df = st.data_editor(df, num_rows="dynamic")
        
        if st.button("💾 Save Database Changes"):
            save_data(edited_df)
            st.success("Database Updated Successfully!")
    else:
        st.info("No data found.")

def client_dashboard():
    st.title("📡 Anand Finserv Dashboard")
    
    col_refresh, col_logout = st.columns([4, 1])
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    with col_logout:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    # --- TABS FOR VIEW ---
    tab1, tab2 = st.tabs(["🚀 Live Calls", "📜 Past Performance"])
    
    df = load_data()
    
    # --- TAB 1: LIVE CALLS ---
    with tab1:
        if df.empty:
            st.info("No Data Available.")
        else:
            # Filter Active
            if 'status' in df.columns:
                active_calls = df[df['status'] == 'Active']
            else:
                active_calls = df
            
            if active_calls.empty:
                st.info("✅ No Open Positions. Market is calm.")
            else:
                for index, row in active_calls.iterrows():
                    cmp = get_cmp(row['stock'])
                    card_class = "buy-card" if row['type'] == "BUY" else "sell-card"
                    text_color = "#00e676" if row['type'] == "BUY" else "#ff5252"
                    
                    # P/L Color for CMP
                    pl_color = "#ffffff"
                    if cmp > 0:
                        if row['type'] == "BUY":
                            pl_color = "#00e676" if cmp >= row['entry'] else "#ff5252"
                        else:
                            pl_color = "#00e676" if cmp <= row['entry'] else "#ff5252"

                    st.markdown(f"""
                    <div class="card {card_class}">
                        <div style="display:flex; justify-content:space-between;">
                            <h3 style="margin:0;">{row['stock']}</h3>
                            <h3 style="margin:0; color:{text_color};">{row['type']}</h3>
                        </div>
                        <hr style="border-color: #444;">
                        <div style="display:flex; justify-content:space-between; font-size:18px;">
                            <span>Entry: {row['entry']}</span>
                            <span>Target: {row['target']}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:18px; margin-top:5px;">
                            <span>SL: <span style="color:#ff5252">{row['sl']}</span></span>
                            <span>CMP: <b style="color:{pl_color}; font-size:22px;">{cmp}</b></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # --- TAB 2: PAST PERFORMANCE ---
    with tab2:
        st.subheader("📊 Trade History")
        
        if df.empty or 'status' not in df.columns:
            st.info("No history found.")
        else:
            # Filter NOT Active (Closed/Target Hit/SL Hit)
            history = df[df['status'] != 'Active'].copy()
            
            if history.empty:
                st.info("No closed trades yet.")
            else:
                # Calculate Points
                history['Points Booked'] = history.apply(calculate_pnl, axis=1)
                
                # Show key columns
                display_cols = ['date', 'stock', 'type', 'status', 'entry', 'exit_price', 'Points Booked']
                
                # Verify columns exist before showing
                available_cols = [c for c in display_cols if c in history.columns]
                final_history = history[available_cols]
                
                # Color Styling function
                def highlight_pnl(val):
                    color = '#00e676' if val > 0 else '#ff5252' if val < 0 else 'white'
                    return f'color: {color}; font-weight: bold;'

                # Display styled dataframe
                st.dataframe(
                    final_history.style.map(highlight_pnl, subset=['Points Booked']),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Total PnL Summary
                total_pts = history['Points Booked'].sum()
                color = "green" if total_pts >= 0 else "red"
                st.markdown(f"### 🏁 Total Points Booked: :{color}[{total_pts}]")

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





