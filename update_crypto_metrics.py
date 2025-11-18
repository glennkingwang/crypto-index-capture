import requests
import time
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import gspread.utils

SHEET_KEY = "1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ"
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate", "Exec Time (UTC)", "Exec Time (Taiwan)"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).worksheet("工作表1")

def safe_value(val):
    return "N/A" if val is None else str(val)

# --- 共用 API 請求函數 ---
def _get_json(url, timeout=5, retries=3, sleep=1.0):
    for i in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"GET {url} 失敗({i+1}/{retries}):", e)
            time.sleep(sleep)
    return None

# --- API 抓取函數 ---
def fetch_cfgi():
    data = _get_json("https://api.alternative.me/fng/")
    print("CFGI API 回傳:", data)
    try:
        arr = data.get("data", []) if data else []
        return int(arr[0]["value"]) if arr else None
    except Exception as e:
        print("parse cfgi error:", e); return None

def fetch_btc_d():
    data = _get_json("https://api.coingecko.com/api/v3/global")
    print("BTC-D API 回傳:", data)
    try:
        btc = data.get("data", {}).get("market_cap_percentage", {}).get("btc") if data else None
        return round(float(btc), 2) if btc is not None else None
    except Exception as e:
        print("parse btc_d error:", e); return None

def fetch_long_short_ratio():
    data = _get_json("https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1")
    print("Long/Short API 回傳:", data)
    try:
        if isinstance(data, list) and data:
            return round(float(data[0]["longShortRatio"]), 2)
        return None
    except Exception as e:
        print("parse long_short error:", e); return None

def fetch_open_interest():
    data = _get_json("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT")
    print("Open Interest API 回傳:", data)
    try:
        val = data.get("openInterest") if data else None
        return round(float(val), 2) if val is not None else None
    except Exception as e:
        print("parse open_interest error:", e); return None

def fetch_funding_rate():
    data = _get_json("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1")
    print("Funding Rate API 回傳:", data)
    try:
        if isinstance(data, list) and data:
            return round(float(data[0]["fundingRate"]) * 100, 4)
        return None
    except Exception as e:
        print("parse funding_rate error:", e); return None

# --- Header 檢查 ---
def ensure_header():
    current = sheet.row_values(1)
    if current != HEADER_ROW:
        print("Header 不一致，更新第 1 列")
        if sheet.row_count < 1:
            sheet.add_rows(1)
        if sheet.col_count < len(HEADER_ROW):
            sheet.add_cols(len(HEADER_ROW) - sheet.col_count)
        sheet.update('A1:' + gspread.utils.rowcol_to_a1(1, len(HEADER_ROW)), [HEADER_ROW])
    else:
        print("Header OK")

# --- 更新 Google Sheet ---
def update_sheet_data():
    print("開始更新 Google Sheet...")
    now_utc = datetime.now(timezone.utc)
    now_tw  = now_utc + timedelta(hours=8)

    today         = now_utc.strftime("%Y-%m-%d")
    exec_time_utc = now_utc.strftime("%H:%M:%S (UTC)")
    exec_time_tw  = now_tw.strftime("%Y-%m-%d %H:%M:%S (Taiwan)")

    try:
        cfgi = fetch_cfgi()
        btc_d = fetch_btc_d()
        ls    = fetch_long_short_ratio()
        oi    = fetch_open_interest()
        fr    = fetch_funding_rate()
    except Exception as e:
        print("API 抓取失敗:", e)
        cfgi = btc_d = ls = oi = fr = None

    row = [
        safe_value(today),
        safe_value(cfgi),
        safe_value(btc_d),
        safe_value(ls),
        safe_value(oi),
        safe_value(fr),
        safe_value(exec_time_utc),
        safe_value(exec_time_tw)
    ]

    print("Row before append:", row)
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print("寫入完成！")
    except Exception as e:
        print("Google Sheet 寫入失敗:", e)

if __name__ == "__main__":
    print("程式開始執行...")
    ensure_header()
    try:
        update_sheet_data()
    except Exception as e:
        print("update_sheet_data 發生錯誤:", e)
    print("程式結束。")
