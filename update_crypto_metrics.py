import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# --- Google Sheets 設置 ---
SHEET_KEY = "你的表單ID"   # 請替換成你的 Google Sheet ID
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate", "Exec Time"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).sheet1

# --- 安全值轉換，避免 None 變成空白 ---
def safe_value(val):
    return val if val is not None else "N/A"

# --- API 函數 ---
def fetch_cfgi():
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if data:
            return int(data[0]["value"])
    except Exception as e:
        print("fetch_cfgi error:", e)
    return None

def fetch_btc_d():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        r.raise_for_status()
        btc = r.json().get("data", {}).get("market_cap_percentage", {}).get("btc")
        if btc is not None:
            return round(btc, 2)
    except Exception as e:
        print("fetch_btc_d error:", e)
    return None

def fetch_long_short_ratio():
    try:
        time.sleep(1)
        r = requests.get(
            "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1",
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return round(float(data[0]["longShortRatio"]), 2)
    except Exception as e:
        print("fetch_long_short_ratio error:", e)
    return None

def fetch_open_interest():
    try:
        time.sleep(1)
        r = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", timeout=10)
        r.raise_for_status()
        data = r.json()
        if "openInterest" in data:
            return round(float(data["openInterest"]), 2)
    except Exception as e:
        print("fetch_open_interest error:", e)
    return None

def fetch_funding_rate():
    try:
        time.sleep(1)
        r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1", timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return round(float(data[0]["fundingRate"]) * 100, 4)
    except Exception as e:
        print("fetch_funding_rate error:", e)
    return None

# --- 更新 Google Sheet ---
def ensure_header():
    try:
        current = sheet.row_values(1)
        if current != HEADER_ROW:
            print("Header missing/incorrect. Inserting...")
            sheet.insert_row(HEADER_ROW, 1)
    except Exception as e:
        print("Header check error:", e)
        sheet.insert_row(HEADER_ROW, 1)

def update_sheet_data():
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    exec_time = now.strftime("%H:%M:%S (UTC)")

    # 抓取數據
    cfgi = fetch_cfgi()
    btc_d = fetch_btc_d()
    ls = fetch_long_short_ratio()
    oi = fetch_open_interest()
    fr = fetch_funding_rate()

    # 組合 row，確保不會空白
    row = [
        today,
        safe_value(cfgi),
        safe_value(btc_d),
        safe_value(ls),
        safe_value(oi),
        safe_value(fr),
        exec_time
    ]

    print("Row to append:", row)  # 寫入前先確認
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"--- {today} metrics updated successfully ---")
    except Exception as e:
        print("Append error:", e)

# --- 主程式 ---
if __name__ == "__main__":
    ensure_header()
    update_sheet_data()
