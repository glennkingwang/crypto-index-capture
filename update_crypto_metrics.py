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

# **[新增]**：模擬瀏覽器的 User-Agent 標頭
USER_AGENT_HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
}

# **[新增]**：定義標題行
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate", "Exec Time"]

# --- API 獲取函數 (v5 - 全部加入 User-Agent) ---

def fetch_cfgi():
    """1. 獲取恐懼與貪婪指數 (來源: Alternative.me)"""
    try:
        r = requests.get("https://api.alternative.me/fng/", headers=USER_AGENT_HEADER, timeout=10)
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
    """2. 獲取 BTC 市佔率 (來源: CoinGecko)"""
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", headers=USER_AGENT_HEADER, timeout=10)
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
    """3. 獲取多空比 (來源: CoinGlass)"""
    try:
        time.sleep(1)
        r = requests.get("https://api.coinglass.com/api/v3/futures/long-short-accounts?symbol=BTC", headers=USER_AGENT_HEADER, timeout=10)
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
    """4. 獲取未平倉量 (來源: CoinGlass)"""
    try:
        time.sleep(1)
        r = requests.get("https://api.coinglass.com/api/v3/futures/open-interest-history?symbol=BTC&time_type=h1&limit=1", headers=USER_AGENT_HEADER, timeout=10)
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
    """5. 獲取資金費率 (來源: CoinGlass)"""
    try:
        time.sleep(1)
        r = requests.get("https://api.coinglass.com/api/v3/futures/funding-rate-history?symbol=BTC&time_type=h1&limit=1", headers=USER_AGENT_HEADER, timeout=10)
        r.raise_for_status()
        data = r.json().get('data')
        if data and len(data) > 0 and 'fundingRate' in data[0]:
            return round(float(data[0]['fundingRate']) * 100, 4)
        else:
            print(f"Error fetch_funding_rate (CoinGlass): Invalid data. Response: {r.text}")
            return None
    except Exception as e:
        print(f"Error in fetch_funding_rate (CoinGlass): {e}")
        return None

# --- 資料更新函數 ---

def update_sheet_data():
    """僅獲取所有數據並更新至 Google Sheet"""
    
    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    exec_time = now.strftime("%H:%M:%S (UTC)")
    
    print(f"Fetching data at {exec_time}...")
    
    row = [
        today_date,
        fetch_cfgi(),
        fetch_btc_d(),
        fetch_long_short_ratio(),
        fetch_open_interest(),
        fetch_funding_rate(),
        exec_time
    ]
    
    try:
        sheet.append_row(row)
        print(f"--- {today_date} metrics updated successfully ---")
        print(f"Data: {row}")
    except Exception as e:
        print(f"Error: Failed to append row to Google Sheet. Error: {e}")
        print(f"Data that failed to append: {row}")

# --- 主執行區塊 ---

if __name__ == "__main__":
    
    # **[新增]**：檢查並插入標題行
    try:
        current_header = sheet.row_values(1)
        if current_header != HEADER_ROW:
            print("Header not found or incorrect. Inserting new header...")
            # 插入新標題在第一行
            sheet.insert_row(HEADER_ROW, 1)
            print("Header inserted.")
        else:
            print("Header is correct. Skipping insertion.")
    except gspread.exceptions.APIError as e:
        # 處理完全空白的表格
        if 'range' in str(e): # 判斷是否為範圍錯誤 (A1不存在)
            print("Sheet appears to be empty. Inserting header...")
            sheet.insert_row(HEADER_ROW, 1)
            print("Header inserted.")
        else:
            raise e # 拋出其他 API 錯誤

    # 執行資料更新
    update_sheet_data()
