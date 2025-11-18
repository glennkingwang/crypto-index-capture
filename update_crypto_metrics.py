import requests
import time
from datetime import datetime, timezone, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 全域設定 ---
API_DELAY = 5   # 每次 API 呼叫之間的延遲秒數，修改這裡即可

# --- Google Sheets 設置 ---
SHEET_KEY = "1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ"
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Open Interest", "Funding Rate", "L/S value", "Exec Time (Taiwan)"]

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

# --- L/S 三家交易所 ---
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

# --- 更新 Google Sheet ---
def update_sheet_data():
    now_tw = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    today = now_tw.strftime("%Y-%m-%d")
    exec_time_tw = now_tw.strftime("%Y-%m-%d %H:%M:%S (Taiwan)")

    all_rows = sheet.get_all_values()
    last_row = all_rows[-1] if all_rows else []
    last_date = last_row[0] if last_row else None

    # 如果是新的一天 → 新增一列完整紀錄
    if last_date != today:
        cfgi = fetch_cfgi(); time.sleep(API_DELAY)
        btc_d = fetch_btc_d(); time.sleep(API_DELAY)
        oi = fetch_open_interest(); time.sleep(API_DELAY)
        fr = fetch_funding_rate(); time.sleep(API_DELAY)

        ls_binance = fetch_long_short_binance(); time.sleep(API_DELAY)
        ls_okx = fetch_long_short_okx(); time.sleep(API_DELAY)
        ls_bybit = fetch_long_short_bybit()
        ls_final = ls_binance or ls_okx or ls_bybit

        row = [
            safe_value(today),
            safe_value(cfgi),
            safe_value(btc_d),
            safe_value(oi),
            safe_value(fr),
            safe_value(ls_final),
            safe_value(exec_time_tw)
        ]
        print("New day row:", row)
        sheet.append_row(row, value_input_option="USER_ENTERED")

    else:
        # 同一天 → 只更新 N/A 欄位
        new_row = last_row[:]

        if last_row[1] == "N/A":
            val = fetch_cfgi()
            if val is not None: new_row[1] = str(val)

        if last_row[2] == "N/A":
            val = fetch_btc_d()
            if val is not None: new_row[2] = str(val)

        if last_row[3] == "N/A":
            val = fetch_open_interest()
            if val is not None: new_row[3] = str(val)

        if last_row[4] == "N/A":
            val = fetch_funding_rate()
            if val is not None: new_row[4] = str(val)

        if last_row[5] == "N/A":
            ls_binance = fetch_long_short_binance(); time.sleep(API_DELAY)
            ls_okx = fetch_long_short_okx(); time.sleep(API_DELAY)
            ls_bybit = fetch_long_short_bybit()
            ls_final = ls_binance or ls_okx or ls_bybit
            if ls_final is not None: new_row[5] = str(ls_final)

        # 更新執行時間（永遠更新）
        new_row[6] = exec_time_tw

        print("Same day row updated:", new_row)
        sheet.update(values=[new_row], range_name=f"A{len(all_rows)}:G{len(all_rows)}")

if __name__ == "__main__":
    ensure_header()
    update_sheet_data()
