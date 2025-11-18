import requests
import time
from datetime import datetime, timezone, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Google Sheets 設置 ---
SHEET_KEY = "1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ"
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Open Interest", "Funding Rate", "L/S (Binance)", "Exec Time (Taiwan)"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).worksheet("工作表1")

def safe_value(val):
    return "N/A" if val is None else str(val)

# --- API 函數 ---
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

# --- Header 檢查 ---
def ensure_header():
    current = sheet.row_values(1)
    if current != HEADER_ROW:
        sheet.insert_row(HEADER_ROW, 1)

# --- 更新 Google Sheet ---
def update_sheet_data():
    now_tw = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    today = now_tw.strftime("%Y-%m-%d")
    exec_time_tw = now_tw.strftime("%Y-%m-%d %H:%M:%S (Taiwan)")

    cfgi = fetch_cfgi()
    time.sleep(2)

    btc_d = fetch_btc_d()
    time.sleep(2)

    oi = fetch_open_interest()
    time.sleep(2)

    fr = fetch_funding_rate()
    time.sleep(2)

    ls_binance = fetch_long_short_binance()

    row = [
        safe_value(today),
        safe_value(cfgi),
        safe_value(btc_d),
        safe_value(oi),
        safe_value(fr),
        safe_value(ls_binance),
        safe_value(exec_time_tw)
    ]

    print("Row before append:", row)
    sheet.append_row(row, value_input_option="USER_ENTERED")

if __name__ == "__main__":
    ensure_header()
    update_sheet_data()
