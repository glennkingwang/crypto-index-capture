import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# --- Google Sheets 設置 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ").sheet1

# --- API 基礎網址 ---
# 我們將幣安的 URL 提出來，並套上代理
PROXY_URL = "https://api.allorigins.win/raw?url="
BINANCE_FAPI_URL = "https://fapi.binance.com"

# --- API 獲取函數 (健壯版本 v3) ---

def fetch_cfgi():
    """獲取恐懼與貪婪指數 (來源: Alternative.me)"""
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        r.raise_for_status()
        data = r.json().get('data')
        if data and len(data) > 0:
            return int(data[0]['value'])
        else:
            print("Error fetch_cfgi: API returned empty or invalid data.")
            return None
    except Exception as e:
        print(f"Error in fetch_cfgi: {e}")
        return None

def fetch_btc_d():
    """獲取 BTC 市佔率 (來源: CoinGecko)"""
    try:
        r = requests.get("https://api.coinglass.com/api/v3/global", timeout=10)
        r.raise_for_status()
        btc_percentage = r.json().get('data', {}).get('market_cap_percentage', {}).get('btc')
        if btc_percentage is not None:
            return round(btc_percentage, 2)
        else:
            print("Error fetch_btc_d: Could not parse BTC dominance from response.")
            return None
    except Exception as e:
        print(f"Error in fetch_btc_d: {e}")
        return None

def fetch_long_short_ratio():
    """獲取多空比 (來源: Binance, 透過代理)"""
    try:
        # **[修改]**：套用代理 URL
        original_url = f"{BINANCE_FAPI_URL}/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1"
        proxied_url = f"{PROXY_URL}{original_url}"
        
        r = requests.get(proxied_url, timeout=15) # 代理可能較慢，延長 timeout
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return round(float(data[0]['longShortRatio']), 2)
        else:
            print(f"Error fetch_long_short_ratio: API (via proxy) returned empty list. Response: {data}")
            return None
    except Exception as e:
        print(f"Error in fetch_long_short_ratio: {e}")
        return None

def fetch_open_interest():
    """獲取未平倉量 (來源: Binance, 透過代理)"""
    try:
        # **[修改]**：套用代理 URL
        original_url = f"{BINANCE_FAPI_URL}/fapi/v1/openInterest?symbol=BTCUSDT"
        proxied_url = f"{PROXY_URL}{original_url}"

        r = requests.get(proxied_url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data and 'openInterest' in data:
            return round(float(data['openInterest']), 2)
        else:
            print(f"Error fetch_open_interest: 'openInterest' key not in response (via proxy). Response: {data}")
            return None
    except Exception as e:
        print(f"Error in fetch_open_interest: {e}")
        return None

def fetch_funding_rate():
    """獲取資金費率 (來源: Binance, 透過代理)"""
    try:
        # **[修改]**：套用代理 URL
        original_url = f"{BINANCE_FAPI_URL}/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1"
        proxied_url = f"{PROXY_URL}{original_url}"
        
        r = requests.get(proxied_url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return round(float(data[0]['fundingRate']) * 100, 4)
        else:
            print(f"Error fetch_funding_rate: API (via proxy) returned empty list. Response: {data}")
            return None
    except Exception as e:
        print(f"Error in fetch_funding_rate: {e}")
        return None

# --- 主執行函數 ---

def update_sheet():
    """獲取所有數據並更新至 Google Sheet"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    print("Fetching data (using proxy for Binance)...")
    
    row = [
        today,
        fetch_cfgi(),
        fetch_btc_d(),
        fetch_long_short_ratio(),
        fetch_open_interest(),
        fetch_funding_rate()
    ]
    
    try:
        sheet.append_row(row)
        print(f"--- {today} metrics updated successfully ---")
        print(f"Data: {row}")
    except Exception as e:
        print(f"Error: Failed to append row to Google Sheet. Error: {e}")
        print(f"Data that failed to append: {row}")

if __name__ == "__main__":
    update_sheet()
