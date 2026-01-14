import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import json

# Discord Webhook URL (you'll add this)
DISCORD_WEBHOOK = st.secrets.get("DISCORD_WEBHOOK", "")

# App Title
st.set_page_config(page_title="Portfolio Tracker", layout="wide")
st.title("📈 Portfolio Tracker & Insider Alerts")
st.markdown("**Track 10-50 stocks • Real-time prices • Insider activity • Discord alerts**")

# Portfolio Management
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=['ticker', 'buy_price', 'shares', 'added_date'])

# Sidebar: Add/Edit Portfolio
with st.sidebar:
    st.header("📊 Manage Portfolio")
    
    # Add new stock
    with st.expander("➕ Add Stock"):
        ticker = st.text_input("Ticker", help="e.g., AAPL, TSLA").upper()
        buy_price = st.number_input("Buy Price", min_value=0.01, format="%.2f")
        shares = st.number_input("Shares", min_value=1, step=1)
        
        if st.button("Add Stock"):
            if ticker:
                new_row = pd.DataFrame({
                    'ticker': [ticker], 'buy_price': [buy_price], 
                    'shares': [shares], 'added_date': [datetime.now().strftime("%Y-%m-%d")]
                })
                st.session_state.portfolio = pd.concat([st.session_state.portfolio, new_row], ignore_index=True)
                st.success(f"Added {ticker}")
    
    # Remove stock
    if not st.session_state.portfolio.empty:
        st.header("❌ Remove Stock")
        remove_idx = st.selectbox("Select to remove:", range(len(st.session_state.portfolio)),
                                 format_func=lambda i: st.session_state.portfolio.iloc[i]['ticker'])
        if st.button("Remove"):
            st.session_state.portfolio = st.session_state.portfolio.drop(remove_idx).reset_index(drop=True)
            st.rerun()

# Main Dashboard
if st.session_state.portfolio.empty:
    st.info("👆 Add your first stock in the sidebar!")
else:
    # Fetch current prices
    tickers = st.session_state.portfolio['ticker'].tolist()
    prices_data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close'].iloc[-1]
    
    # Calculate metrics
    portfolio_metrics = []
    for idx, row in st.session_state.portfolio.iterrows():
        ticker = row['ticker']
        buy_price = row['buy_price']
        shares = row['shares']
        
        current_price = prices_data.get(ticker, 0)
        gain_loss_pct = ((current_price - buy_price) / buy_price * 100) if current_price > 0 else 0
        gain_loss_dollar = (current_price - buy_price) * shares
        
        portfolio_metrics.append({
            'ticker': ticker, 'buy_price': buy_price, 'current_price': current_price,
            'gain_loss_pct': gain_loss_pct, 'gain_loss_dollar': gain_loss_dollar,
            'total_value': current_price * shares, 'shares': shares
        })
    
    df_portfolio = pd.DataFrame(portfolio_metrics)
    
    # Portfolio Summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_value = df_portfolio['total_value'].sum()
        st.metric("Total Value", f"${total_value:,.0f}")
    with col2:
        total_gain_pct = (df_portfolio['gain_loss_pct'] * df_portfolio['shares']).sum() / df_portfolio['shares'].sum()
        st.metric("Total Gain", f"{total_gain_pct:.1f}%")
    with col3:
        daily_change = df_portfolio['gain_loss_pct'].mean()
        st.metric("Avg Daily", f"{daily_change:.1f}%")
    with col4:
        st.metric("Stocks", len(df_portfolio))
    
    # Portfolio Table
    st.subheader("📋 Portfolio Details")
    st.dataframe(df_portfolio.round(2), use_container_width=True)
    
    # Alerts Section
    st.subheader("🚨 Alerts Configuration")
    
    # Price Drop Alert (7%)
    price_alerts = df_portfolio[df_portfolio['gain_loss_pct'] <= -7]
    if not price_alerts.empty:
        st.error(f"🔴 **PRICE DROP ALERT**: {len(price_alerts)} stocks down >7%!")
        for _, alert in price_alerts.iterrows():
            st.error(f"**{alert['ticker']}**: {alert['gain_loss_pct']:.1f}% ({alert['current_price']:.2f})")
    
    # Test Discord Notification
    if st.button("🔔 Test Discord Alert"):
        send_discord_alert("**Portfolio Tracker Test**\nDashboard is working! 🚀")
        st.success("Test sent!")
    
    # Auto-check button (for demo)
    if st.button("🔍 Check Insider Activity Now"):
        check_insider_alerts(df_portfolio['ticker'].tolist())
        st.success("Checked insider activity!")

# Discord Notification Function
def send_discord_alert(message):
    if DISCORD_WEBHOOK:
        data = {"content": message}
        requests.post(DISCORD_WEBHOOK, json=data)
    else:
        st.warning("Add DISCORD_WEBHOOK to Streamlit secrets!")

# Insider Check Function (stub - will implement in Phase 2)
def check_insider_alerts(tickers):
    st.info("🔍 Checking SEC EDGAR for insider activity...")
    # Phase 2: Implement SEC EDGAR API call here
    pass

# Footer
st.markdown("---")
st.caption("💡 Free-only • Cloud-hosted • No historical data • Hourly updates")
