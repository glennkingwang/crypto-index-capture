import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time  # 建議加入 time 模組

# --- Google Sheets 設置 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ").sheet1

# --- API 獲取函數 (健壯版本) ---

def fetch_cfgi():
    """獲取恐懼與貪婪指數"""
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        r.raise_for_status()  # 檢查 HTTP 錯誤
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
    """獲取 BTC 市佔率"""
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        r.raise_for_status()
        # 對於深度嵌套的 dict，使用 .get() 更安全
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
    """獲取多空比 (Binance)"""
    try:
        # 幣安 API 速率限制嚴格，增加一點延遲
        time.sleep(1) 
        r = requests.get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1", timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return round(float(data[0]['longShortRatio']), 2)
        else:
            # 這是上次發生錯誤的地方
            print(f"Error fetch_long_short_ratio: API returned empty list. Response: {data}")
            return None
    except Exception as e:
        print(f"Error in fetch_long_short_ratio: {e}")
        return None

def fetch_open_interest():
    """獲取未平倉量 (Binance)"""
    try:
        time.sleep(1)
        r = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", timeout=10)
        r.raise_for_status()
        data = r.json()
        if data and 'openInterest' in data:
            return round(float(data['openInterest']), 2)
        else:
            print(f"Error fetch_open_interest: 'openInterest' key not in response. Response: {data}")
            return None
    except Exception as e:
        print(f"Error in fetch_open_interest: {e}")
        return None

def fetch_funding_rate():
    """獲取資金費率 (Binance)"""
    try:
        time.sleep(1)
        r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1", timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return round(float(data[0]['fundingRate']) * 100, 4)
        else:
            print(f"Error fetch_funding_rate: API returned empty list. Response: {data}")
            return None
    except Exception as e:
        print(f"Error in fetch_funding_rate: {e}")
        return None

# --- 主執行函數 ---

def update_sheet():
    """獲取所有數據並更新至 Google Sheet"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    print("Fetching data...")
    
    # 依次呼叫所有函數，如果某個函數返回 None，該變數將儲存 None
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
