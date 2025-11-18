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

# --- API 獲取函數 (健壯版本 v4) ---

def fetch_cfgi():
    """1. 獲取恐懼與貪婪指數 (來源: Alternative.me)"""
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
    """2. 獲取 BTC 市佔率 (來源: CoinGecko) - [已修正回 v1 的網址]"""
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
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
    """3. 獲取多空比 (來源: CoinGlass) - [新 API 來源]"""
    try:
        # 使用 CoinGlass 的 long-short-accounts 端點
        time.sleep(1) # 禮貌性延遲
        r = requests.get("https://api.coinglass.com/api/v3/futures/long-short-accounts?symbol=BTC", timeout=10)
        r.raise_for_status()
        data = r.json().get('data')
        if data and 'longShortRatio' in data:
            return round(float(data['longShortRatio']), 2)
        else:
            print(f"Error fetch_long_short_ratio (CoinGlass): Invalid data. Response: {r.text}")
            return None
    except Exception as e:
        print(f"Error in fetch_long_short_ratio (CoinGlass): {e}")
        return None

def fetch_open_interest():
    """4. 獲取未平倉量 (來源: CoinGlass) - [新 API 來源]"""
    try:
        # 使用 CoinGlass 的 open-interest-history 端點
        time.sleep(1)
        r = requests.get("https://api.coinglass.com/api/v3/futures/open-interest-history?symbol=BTC&time_type=h1&limit=1", timeout=10)
        r.raise_for_status()
        data = r.json().get('data')
        if data and len(data) > 0 and 'openInterest' in data[0]:
            return round(float(data[0]['openInterest']), 2)
        else:
            print(f"Error fetch_open_interest (CoinGlass): Invalid data. Response: {r.text}")
            return None
    except Exception as e:
        print(f"Error in fetch_open_interest (CoinGlass): {e}")
        return None

def fetch_funding_rate():
    """5. 獲取資金費率 (來源: CoinGlass) - [新 API 來源]"""
    try:
        # 使用 CoinGlass 的 funding-rate-history 端點
        time.sleep(1)
        r = requests.get("https://api.coinglass.com/api/v3/futures/funding-rate-history?symbol=BTC&time_type=h1&limit=1", timeout=10)
        r.raise_for_status()
        data = r.json().get('data')
        if data and len(data) > 0 and 'fundingRate' in data[0]:
            # 原始邏輯：將費率轉為百分比
            return round(float(data[0]['fundingRate']) * 100, 4)
        else:
            print(f"Error fetch_funding_rate (CoinGlass): Invalid data. Response: {r.text}")
            return None
    except Exception as e:
        print(f"Error in fetch_funding_rate (CoinGlass): {e}")
        return None

# --- 主執行函數 ---

def update_sheet():
    """獲取所有數據並更新至 Google Sheet"""
    
    # **[新增]**：獲取日期和時間
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    exec_time = now.strftime("%H:%M:%S (UTC)") # GitHub Actions 預設使用 UTC 時間
    
    print(f"Fetching data at {exec_time}...")
    
    # **[修改]**：在 row 的最後加入 exec_time
    row = [
        today_date,
        fetch_cfgi(),               # B 欄
        fetch_btc_d(),              # C 欄
        fetch_long_short_ratio(),   # D 欄
        fetch_open_interest(),      # E 欄
        fetch_funding_rate(),       # F 欄
        exec_time                   # G 欄 (新)
    ]
    
    try:
        sheet.append_row(row)
        print(f"--- {today_date} metrics updated successfully ---")
        print(f"Data: {row}")
    except Exception as e:
        print(f"Error: Failed to append row to Google Sheet. Error: {e}")
        print(f"Data that failed to append: {row}")

if __name__ == "__main__":
    update_sheet()
