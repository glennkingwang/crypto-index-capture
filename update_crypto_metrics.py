import requests
from datetime import datetime, timedelta, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SHEET_KEY = "1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ"
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate", "Exec Time (UTC)", "Exec Time (Taiwan)"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).worksheet("工作表1")

def safe_value(val):
    return str(val) if val is not None else "N/A"

# --- API 抓取函數 ---
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
        data = r.json()
        btc = data.get("data", {}).get("market_cap_percentage", {}).get("btc")
        return round(btc, 2) if btc is not None else None
    except Exception as e:
        print("fetch_btc_d error:", e)
        return None

def fetch_long_short_ratio():
    try:
        r = requests.get(
            "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1",
            timeout=5
        )
        r.raise_for_status()
        data = r.json()
        return round(float(data[0]["longShortRatio"]), 2) if isinstance(data, list) and data else None
    except Exception as e:
        print("fetch_long_short_ratio error:", e)
        return None

def fetch_open_interest():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", timeout=5)
        r.raise_for_status()
        data = r.json()
        return round(float(data["openInterest"]), 2) if "openInterest" in data else None
    except Exception as e:
        print("fetch_open_interest error:", e)
        return None

def fetch_funding_rate():
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1", timeout=5)
        r.raise_for_status()
        data = r.json()
        return round(float(data[0]["fundingRate"]) * 100, 4) if isinstance(data, list) and data else None
    except Exception as e:
        print("fetch_funding_rate error:", e)
        return None

def ensure_header():
    current = sheet.row_values(1)
    if current != HEADER_ROW:
        print("Header 不正確，插入新 Header")
        sheet.insert_row(HEADER_ROW, 1)
    else:
        print("Header OK")

def update_sheet_data():
    print("開始更新 Google Sheet...")

    # ✅ 兼容 Python 3.10 的寫法
    now_utc = datetime.now(timezone.utc)  
    now_tw = now_utc + timedelta(hours=8)  # 台灣時間 UTC+8

    today = now_utc.strftime("%Y-%m-%d")
    exec_time_utc = now_utc.strftime("%H:%M:%S (UTC)")
    exec_time_tw = now_tw.strftime("%Y-%m-%d %H:%M:%S (Taiwan)")

    try:
        cfgi = fetch_cfgi()
        btc_d = fetch_btc_d()
        ls = fetch_long_short_ratio()
        oi = fetch_open_interest()
        fr = fetch_funding_rate()
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

    try:
        print("Row before append:", row)
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
