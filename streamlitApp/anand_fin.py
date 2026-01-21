import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import pytz
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Anand Research 360", layout="wide", page_icon="📈")

# --- CUSTOM CSS FOR 'RESEARCH 360' LOOK ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .metric-card {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 10px;
    }
    .green-border { border-left: 5px solid #00c853 !important; }
    .big-font { font-size: 24px !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- CONNECTIONS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Worksheet ka naam agar 'Sheet1' nahi hai to change karein
        data = conn.read(worksheet="Sheet1", ttl="5s")
        required_cols = ['id', 'stock', 'type', 'entry', 'target', 'sl', 'status', 'exit_price', 'date']
        for col in required_cols:
            if col not in data.columns:
                data[col] = None
        return data
    except Exception as e:
        # Fallback agar connection fail ho
        return pd.DataFrame(columns=['id', 'stock', 'type', 'entry', 'target', 'sl', 'status', 'exit_price', 'date'])

def save_to_sheet(df_to_save):
    try:
        conn.update(worksheet="Sheet1", data=df_to_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Save Error: {e}")
        return False

# --- HELPER FUNCTIONS ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker + ".NS")
        hist = stock.history(period="1y")
        info = stock.info
        return hist, info
    except:
        return None, None

def plot_candle_chart(hist, ticker):
    fig = go.Figure(data=[go.Candlestick(x=hist.index,
                open=hist['Open'], high=hist['High'],
                low=hist['Low'], close=hist['Close'])])
    fig.update_layout(title=f"{ticker} - Daily Chart", template="plotly_dark", height=500)
    return fig

# --- PAGES ---

def login_page():
    st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>🔐 Anand Research 360</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login to Terminal")
            
            if submitted:
                if username == "admin" and password == "anand123":
                    st.session_state.logged_in = True
                    st.session_state.user_type = "Admin"
                    st.rerun()
                elif username == "client" and password == "client123":
                    st.session_state.logged_in = True
                    st.session_state.user_type = "Client"
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

def admin_dashboard():
    st.title("👨‍💻 Admin Control Center")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
        
    # (Yahan aapka purana admin code ayega data publish karne ke liye)
    # Short version for demo:
    st.info("Admin Panel active. Use logic from previous code to publish levels.")
    
    # Show current data
    df = load_data()
    st.dataframe(df)

ddef client_dashboard():
    st.markdown("## 📊 Research 360 Dashboard")
    
    # --- LOAD LIVE LEVELS FROM YOUR SHEET ---
    df = load_data()
    
    if df.empty:
        st.warning("⚠️ Abhi koi levels available nahi hain. Admin panel se add karein.")
        return

    # Filter only Active levels
    active_calls = df[df['status'] == 'Active']

    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("📡 Your Live Calls")
        if active_calls.empty:
            st.info("No Active Calls found in your Google Sheet.")
        else:
            for index, row in active_calls.iterrows():
                # Har level ke liye ek card aur button
                st.markdown(f"""
                <div style='background-color: #1e2130; padding: 10px; border-radius: 5px; border-left: 5px solid {"#00c853" if row["type"]=="BUY" else "#ff4b4b"}; margin-bottom: 5px;'>
                    <h4 style='margin:0;'>{row['stock']}</h4>
                    <p style='margin:0;'>Target: {row['target']} | SL: {row['sl']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Button click karne par session state update hogi
                if st.button(f"View {row['stock']} Chart", key=f"btn_{row['id']}"):
                    st.session_state.selected_ticker = row['stock']

    with col_right:
        # Agar koi ticker select hua hai sheet se, tabhi dikhao
        if 'selected_ticker' in st.session_state:
            ticker = st.session_state.selected_ticker
            st.markdown(f"### 📈 Live Analysis: {ticker}")
            
            hist, info = get_stock_data(ticker)
            
            if hist is not None and not hist.empty:
                # Live Price calculation
                cp = hist['Close'].iloc[-1]
                st.metric(label=f"{ticker} Live Price", value=f"₹{cp:.2f}")
                
                # Show Chart
                fig = plot_candle_chart(hist, ticker)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"Ticker '{ticker}' ka data nahi mil raha. Check spelling in Sheet (e.g., RELIANCE).")
        else:
            st.info("👈 Baayi taraf (left) kisi stock par click karein uska live chart dekhne ke liye.")

    # --- LOAD LIVE LEVELS ---
    df = load_data()
    
    # Layout Split: Left (Menu/Levels), Right (Analysis)
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("📡 Live Calls")
        if not df.empty and 'status' in df.columns:
            active_calls = df[df['status'] == 'Active']
            if active_calls.empty:
                st.info("No Active Calls Today")
            else:
                for index, row in active_calls.iterrows():
                    # Card Design
                    color_class = "green-border" if row['type'] == 'BUY' else "metric-card"
                    st.markdown(f"""
                    <div class="metric-card {color_class}">
                        <h3>{row['stock']} ({row['type']})</h3>
                        <p>Entry: <b>{row['entry']}</b> | Target: <b>{row['target']}</b></p>
                        <p style='color: gray; font-size: 12px;'>SL: {row['sl']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Analyze {row['stock']}", key=f"btn_{index}"):
                        st.session_state.selected_stock = row['stock']
        else:
            st.warning("Data loading...")

    with col_right:
        # Agar koi stock select kiya hai ya default pehla stock
        selected_stock = st.session_state.get('selected_stock', 'RELIANCE')
        
        st.markdown(f"### 📈 Analysis: {selected_stock}")
        
        hist, info = get_stock_data(selected_stock)
        
        if hist is not None:
            # Current Price Display
            current_price = hist['Close'].iloc[-1]
            change = current_price - hist['Open'].iloc[-1]
            color = "green" if change > 0 else "red"
            
            st.markdown(f"""
            <div style='background-color: #262730; padding: 20px; border-radius: 10px; text-align: center;'>
                <h1 style='margin:0;'>₹{current_price:.2f}</h1>
                <h3 style='color: {color}; margin:0;'>{change:.2f} ({ (change/current_price)*100 :.2f}%)</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # TABS for Detail
            tab1, tab2, tab3 = st.tabs(["🕯️ Charts", "📋 Fundamentals", "📰 News"])
            
            with tab1:
                fig = plot_candle_chart(hist, selected_stock)
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                if info:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Market Cap", info.get('marketCap', 'N/A'))
                    c2.metric("PE Ratio", info.get('trailingPE', 'N/A'))
                    c3.metric("52W High", info.get('fiftyTwoWeekHigh', 'N/A'))
                    
                    st.write("**Business Summary:**")
                    st.caption(info.get('longBusinessSummary', 'Not Available')[:300] + "...")
            
            with tab3:
                st.info("News API integration coming soon...")
                
        else:
            st.error("Could not fetch data from Yahoo Finance.")

# --- MAIN APP LOGIC ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    if st.session_state.user_type == "Admin":
        admin_dashboard()
    else:
        client_dashboard()
else:
    login_page()










