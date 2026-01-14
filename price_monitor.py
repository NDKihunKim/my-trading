import os
import yfinance as yf
import pandas as pd
import requests
from supabase import create_client
from datetime import datetime
import pytz

# Get credentials from environment
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_market_open():
    """Check if US market is currently open"""
    tz = pytz.timezone("US/Eastern")
    now = datetime.now(tz)
    
    # Check if weekend
    if now.weekday() > 4:
        print(f"Weekend - market closed")
        return False
    
    # Check market hours (9:30 AM - 4:00 PM ET)
    current_time = now.time()
    market_open = datetime.strptime("09:30", "%H:%M").time()
    market_close = datetime.strptime("23:00", "%H:%M").time()
    
    if market_open <= current_time <= market_close:
        return True
    else:
        print(f"Outside market hours ({current_time})")
        return False

def send_discord_alert(message):
    """Send alert to Discord"""
    if DISCORD_WEBHOOK:
        try:
            response = requests.post(DISCORD_WEBHOOK, json={"content": message})
            print(f"Discord alert sent: {response.status_code}")
        except Exception as e:
            print(f"Error sending Discord alert: {e}")

def check_prices():
    """Main price checking logic"""
    print(f"=== Price Check Started: {datetime.now(pytz.timezone('US/Eastern'))} ===")
    
    if not is_market_open():
        print("Market closed - skipping price check")
        return
    
    # Load portfolio from Supabase
    try:
        resp = supabase.table("portfolio").select("*").execute()
        if not resp.data:
            print("No portfolio data found")
            return
        
        df = pd.DataFrame(resp.data)
        print(f"Loaded {len(df)} stocks from portfolio")
    except Exception as e:
        print(f"Error loading portfolio: {e}")
        return
    
    tickers = df["ticker"].tolist()
    
    # Fetch current prices
    try:
        if len(tickers) == 1:
            data = yf.download(tickers[0], period="1d", interval="1m", progress=False)
            if not data.empty:
                prices_data = {tickers[0]: float(data["Close"].iloc[-1])}
            else:
                prices_data = {}
        else:
            data = yf.download(tickers, period="1d", interval="1m", progress=False)["Close"].iloc[-1]
            if isinstance(data, pd.Series):
                prices_data = data.to_dict()
            else:
                prices_data = {}
        
        print(f"Fetched prices for {len(prices_data)} stocks")
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return
    
    drop_alerts = []
    
    for _, row in df.iterrows():
        ticker = row["ticker"]
        buy_price = float(row["buy_price"])
        standard_price = float(row.get("standard_price", buy_price))
        row_id = row["id"]
        
        current_price = float(prices_data.get(ticker, 0.0))
        if current_price == 0:
            print(f"{ticker}: No price data available")
            continue
        
        print(f"{ticker}: ${current_price:.2f} (standard: ${standard_price:.2f})")
        
        # Update standard_price if new high
        if current_price > standard_price:
            standard_price = current_price
            try:
                supabase.table("portfolio").update(
                    {"standard_price": standard_price}
                ).eq("id", row_id).execute()
                print(f"  → New high! Updated standard_price to ${standard_price:.2f}")
            except Exception as e:
                print(f"  → Error updating standard_price: {e}")
        
        # Check for 7% drop
        drop_pct = (current_price - standard_price) / standard_price * 100
        
        if drop_pct <= -7:
            drop_alerts.append((ticker, standard_price, current_price, drop_pct))
            print(f"  ⚠️ ALERT: {ticker} dropped {drop_pct:.1f}%")
    
    # Send Discord alerts
    if drop_alerts:
        lines = [f"**{ticker}**: {drop_pct:.1f}% drop (${std_price:.2f} → ${curr_price:.2f})" 
                 for ticker, std_price, curr_price, drop_pct in drop_alerts]
        message = "🚨 **Price Drop Alert (7%)**\n\n" + "\n".join(lines)
        send_discord_alert(message)
        print(f"\n✅ Sent {len(drop_alerts)} alert(s) to Discord")
    else:
        print("\n✅ No alerts triggered")
    
    print("=== Price Check Completed ===\n")

if __name__ == "__main__":
    check_prices()
