import requests
import time
from datetime import datetime, timezone, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 全域設定 ---
API_DELAY = 5   # API 呼叫延遲

# --- Google Sheets 設置 ---
SHEET_KEY = "1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ"
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Open Interest", "Funding Rate", "L/S value", "Exec Time (Taiwan)"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).worksheet("工作表1")

def safe_value(val):
    return "N/A" if val is None else str(val)

# --- API 函數 (保持不變) ---
def fetch_cfgi():
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=5)
        r.raise_for_status()
        data = r.json().get("data", [])
        return int(data[0]["value"]) if data else None
    except Exception as e:
        print("fetch_cfgi error:", e)
        return None

def fetch_btc_d():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=5)
        r.raise_for_status()
        btc = r.json().get("data", {}).get("market_cap_percentage", {}).get("btc")
        return round(btc, 2) if btc is not None else None
    except Exception as e:
        print("fetch_btc_d error:", e)
        return None

def fetch_open_interest():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/derivatives/exchanges/binance_futures", timeout=5)
        r.raise_for_status()
        data = r.json()
        return round(float(data.get("open_interest_btc", 0)), 2)
    except Exception as e:
        print("fetch_open_interest error:", e)
        return None

def fetch_funding_rate():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/derivatives", timeout=5)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return round(float(data[0].get("funding_rate", 0)) * 100, 4)
        return None
    except Exception as e:
        print("fetch_funding_rate error:", e)
        return None

# --- L/S 三家交易所 (保持不變) ---
def fetch_long_short_binance():
    try:
        url = "https://fapi.binance.com/futures/data/topLongShortAccountRatio"
        params = {"symbol": "BTCUSDT", "period": "5m", "limit": 1}
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return round(float(data[0]["longShortRatio"]), 2)
        return None
    except Exception as e:
        print("fetch_long_short_binance error:", e)
        return None

def fetch_long_short_okx():
    try:
        url = "https://www.okx.com/api/v5/rubik/stat/contracts-long-short-account-ratio"
        params = {"ccy": "BTC", "period": "5m"}
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json().get("data", [])
        if isinstance(data, list) and data:
            return round(float(data[0]["ratio"]), 2)
        return None
    except Exception as e:
        print("fetch_long_short_okx error:", e)
        return None

def fetch_long_short_bybit():
    try:
        url = "https://api.bybit.com/v5/market/account-ratio"
        params = {"symbol": "BTCUSDT", "period": "5m"}
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json().get("result", {}).get("list", [])
        if isinstance(data, list) and data:
            return round(float(data[0]["longShortRatio"]), 2)
        return None
    except Exception as e:
        print("fetch_long_short_bybit error:", e)
        return None

# --- Header 檢查 ---
def ensure_header():
    current = sheet.row_values(1)
    if current != HEADER_ROW:
        sheet.insert_row(HEADER_ROW, 1)
        sheet.freeze(rows=1)

# --- 更新 Google Sheet (先排序 -> 再更新) ---
def update_sheet_data():
    now_tw = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    today = now_tw.strftime("%Y-%m-%d")
    exec_time_tw = now_tw.strftime("%Y-%m-%d %H:%M:%S (Taiwan)")

    # --- 步驟 1: 先進行排序 (降冪：最新的在上面) ---
    # 這樣可以確保資料順序正確，且如果今天是新的一天，我們可以直接插在第2行
    total_rows = len(sheet.get_all_values())
    if total_rows > 1:
        print("Pre-sorting sheet by Date (Descending)...")
        try:
            sheet.sort((1, 'des'), range=f'A2:G{total_rows}')
        except Exception as e:
            print(f"Sort warning: {e}")
    
    # --- 步驟 2: 排序後，重新讀取所有日期 ---
    # 必須在 sort 之後讀，這樣 index 才是對的
    dates = sheet.col_values(1) 
    
    # --- 步驟 3: 檢查與更新/新增 ---
    if today in dates:
        # === 更新模式 (Update) ===
        row_index = dates.index(today) + 1 
        print(f"Date {today} found at row {row_index}. Updating...")
        
        current_row = sheet.row_values(row_index)
        # 補齊長度防錯
        while len(current_row) < 7:
            current_row.append("N/A")
            
        new_row = current_row[:]

        # 依序檢查 N/A 並更新
        if new_row[1] == "N/A":
            val = fetch_cfgi(); 
            if val is not None: new_row[1] = str(val)
            time.sleep(API_DELAY)

        if new_row[2] == "N/A":
            val = fetch_btc_d(); 
            if val is not None: new_row[2] = str(val)
            time.sleep(API_DELAY)

        if new_row[3] == "N/A":
            val = fetch_open_interest(); 
            if val is not None: new_row[3] = str(val)
            time.sleep(API_DELAY)

        if new_row[4] == "N/A":
            val = fetch_funding_rate(); 
            if val is not None: new_row[4] = str(val)
            time.sleep(API_DELAY)

        if new_row[5] ==
