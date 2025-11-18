import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# --- Google Sheets 設置 ---
SHEET_KEY = "1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ"   # 你的表單 ID
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate", "Exec Time"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# 明確指定分頁名稱「工作表1」
sheet = client.open_by_key(SHEET_KEY).worksheet("工作表1")

# --- 安全值轉換，避免 None 變成空白 ---
def safe_value(val):
    return val if val is not None else "N/A"

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

# --- Header 檢查 ---
def ensure_header():
    try:
        current = sheet.row_values(1)
        if current != HEADER_ROW:
            print("Header missing/incorrect. Inserting...")
            sheet.insert_row(HEADER_ROW, 1)
        else:
            print("Header OK.")
    except Exception as e:
        print("Header check error:", e)
        sheet.insert_row(HEADER_ROW, 1)

# --- 更新 Google Sheet ---
def update_sheet_data():
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    exec_time = now.strftime("%H:%M:%S (UTC)")

    # 並行抓取數據
    tasks = {
        "CFGI": fetch_cfgi,
        "BTC-D": fetch_btc_d,
        "Long/Short": fetch_long_short_ratio,
        "Open Interest": fetch_open_interest,
        "Funding Rate": fetch_funding_rate,
    }

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(func): name for name, func in tasks.items()}
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                results[name] = future.result()
            except Exception as e:
                print(f"{name} future error:", e)
                results[name] = None

    row = [
        today,
        safe_value(results.get("CFGI")),
        safe_value(results.get("BTC-D")),
        safe_value(results.get("Long/Short")),
        safe_value(results.get("Open Interest")),
        safe_value(results.get("Funding Rate")),
        exec_time
    ]

    print("Row to append:", row)
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"--- {today} metrics updated successfully ---")
    except Exception as e:
        print("Append error:", e)

# --- 主程式 ---
if __name__ == "__main__":
    ensure_header()
    update_sheet_data()
