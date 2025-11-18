import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SHEET_KEY = "1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ"
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate", "Exec Time"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_KEY).worksheet("工作表1")

def safe_value(val):
    return str(val) if val is not None else "N/A"

def fetch_long_short_ratio():
    r = requests.get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1", timeout=5)
    data = r.json()
    return round(float(data[0]["longShortRatio"]), 2) if isinstance(data, list) and data else None

def fetch_open_interest():
    r = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", timeout=5)
    data = r.json()
    return round(float(data["openInterest"]), 2) if "openInterest" in data else None

def fetch_funding_rate():
    r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1", timeout=5)
    data = r.json()
    return round(float(data[0]["fundingRate"]) * 100, 4) if isinstance(data, list) and data else None

def fetch_cfgi():
    r = requests.get("https://api.alternative.me/fng/", timeout=5)
    data = r.json().get("data", [])
    return int(data[0]["value"]) if data else None

def fetch_btc_d():
    r = requests.get("https://api.coingecko.com/api/v3/global", timeout=5)
    btc = r.json().get("data", {}).get("market_cap_percentage", {}).get("btc")
    return round(btc, 2) if btc is not None else None

def ensure_header():
    current = sheet.row_values(1)
    if current != HEADER_ROW:
        sheet.insert_row(HEADER_ROW, 1)

def update_sheet_data():
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    exec_time = now.strftime("%H:%M:%S (UTC)")

    cfgi = fetch_cfgi()
    btc_d = fetch_btc_d()
    ls = fetch_long_short_ratio()
    oi = fetch_open_interest()
    fr = fetch_funding_rate()

    row = [
        today,
        safe_value(cfgi),
        safe_value(btc_d),
        safe_value(ls),
        safe_value(oi),
        safe_value(fr),
        exec_time
    ]

    print("Row before append:", row)  # 確認 D/E/F 是否有值
    sheet.append_row(row, value_input_option="USER_ENTERED")

if __name__ == "__main__":
    ensure_header()
    update_sheet_data()
