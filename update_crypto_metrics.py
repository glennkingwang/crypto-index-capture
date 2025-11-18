import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# --- Google Sheets 設置 ---
SHEET_KEY = "你的表單ID"  # 替換成你的 Google Sheet ID
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate", "Exec Time"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).sheet1

# --- 安全值轉換，避免 None 變成空白 ---
def safe_value(val):
    return val if val is not None else "N/A"

# --- 建立可重用的 Session（Keep-Alive + Retry） ---
def make_session():
    s = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return s

# --- API 函數（全部使用相同 session，timeout=5） ---
def fetch_cfgi(session):
    start = time.time()
    try:
        r = session.get("https://api.alternative.me/fng/", timeout=5)
        r.raise_for_status()
        data = r.json().get("data", [])
        val = int(data[0]["value"]) if data else None
        return val, time.time() - start
    except Exception as e:
        print("fetch_cfgi error:", e)
        return None, time.time() - start

def fetch_btc_d(session):
    start = time.time()
    try:
        r = session.get("https://api.coingecko.com/api/v3/global", timeout=5)
        r.raise_for_status()
        btc = r.json().get("data", {}).get("market_cap_percentage", {}).get("btc")
        val = round(btc, 2) if btc is not None else None
        return val, time.time() - start
    except Exception as e:
        print("fetch_btc_d error:", e)
        return None, time.time() - start

def fetch_long_short_ratio(session):
    start = time.time()
    try:
        r = session.get(
            "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1",
            timeout=5
        )
        r.raise_for_status()
        data = r.json()
        val = round(float(data[0]["longShortRatio"]), 2) if isinstance(data, list) and data else None
        return val, time.time() - start
    except Exception as e:
        print("fetch_long_short_ratio error:", e)
        return None, time.time() - start

def fetch_open_interest(session):
    start = time.time()
    try:
        r = session.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", timeout=5)
        r.raise_for_status()
        data = r.json()
        val = round(float(data["openInterest"]), 2) if "openInterest" in data else None
        return val, time.time() - start
    except Exception as e:
        print("fetch_open_interest error:", e)
        return None, time.time() - start

def fetch_funding_rate(session):
    start = time.time()
    try:
        r = session.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1", timeout=5)
        r.raise_for_status()
        data = r.json()
        val = round(float(data[0]["fundingRate"]) * 100, 4) if isinstance(data, list) and data else None
        return val, time.time() - start
    except Exception as e:
        print("fetch_funding_rate error:", e)
        return None, time.time() - start

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

# --- 更新 Google Sheet（並行抓取 + 耗時量測） ---
def update_sheet_data():
    session = make_session()
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    exec_time = now.strftime("%H:%M:%S (UTC)")

    start_total = time.time()

    # 並行抓取所有數據
    tasks = {
        "CFGI": lambda: fetch_cfgi(session),
        "BTC-D": lambda: fetch_btc_d(session),
        "Long/Short": lambda: fetch_long_short_ratio(session),
        "Open Interest": lambda: fetch_open_interest(session),
        "Funding Rate": lambda: fetch_funding_rate(session),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_map = {executor.submit(func): name for name, func in tasks.items()}
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                val, elapsed = future.result()
                results[name] = (val, elapsed)
            except Exception as e:
                print(f"{name} future error:", e)
                results[name] = (None, None)

    # 轉換值，避免空白
    row = [
        today,
        safe_value(results.get("CFGI", (None,))[0]),
        safe_value(results.get("BTC-D", (None,))[0]),
        safe_value(results.get("Long/Short", (None,))[0]),
        safe_value(results.get("Open Interest", (None,))[0]),
        safe_value(results.get("Funding Rate", (None,))[0]),
        exec_time
    ]

    total_elapsed = time.time() - start_total

    # 打印耗時與即將寫入的資料
    print("耗時資訊（秒）:")
    for k in ["CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate"]:
        print(f"- {k}: {round(results.get(k, (None, 0))[1] or 0, 3)}")
    print(f"- Total: {round(total_elapsed, 3)}")
    print("Row to append:", row)

    # 寫入 Google Sheet
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"--- {today} metrics updated successfully ---")
    except Exception as e:
        print("Append error:", e)

# --- 主程式 ---
if __name__ == "__main__":
    ensure_header()
    update_sheet_data()
