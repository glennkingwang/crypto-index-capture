import requests
from datetime import datetime, UTC, timedelta
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

# --- API 函數 (略，保持你原本的 fetch_cfgi / fetch_btc_d / fetch_long_short_ratio / fetch_open_interest / fetch_funding_rate) ---

def ensure_header():
    current = sheet.row_values(1)
    if current != HEADER_ROW:
        print("Header 不正確，插入新 Header")
        sheet.insert_row(HEADER_ROW, 1)
    else:
        print("Header OK")

def update_sheet_data():
    print("開始更新 Google Sheet...")

    # ✅ 新版 datetime 寫法
    now_utc = datetime.now(UTC)  
    now_tw = now_utc + timedelta(hours=8)  # 台灣時間 UTC+8

    today = now_utc.strftime("%Y-%m-%d")
    exec_time_utc = now_utc.strftime("%H:%M:%S (UTC)")
    exec_time_tw = now_tw.strftime("%Y-%m-%d %H:%M:%S (Taiwan)")

    cfgi = fetch_cfgi()
    btc_d = fetch_btc_d()
    ls = fetch_long_short_ratio()
    oi = fetch_open_interest()
    fr = fetch_funding_rate()

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
    sheet.append_row(row, value_input_option="USER_ENTERED")
    print("寫入完成！")

if __name__ == "__main__":
    print("程式開始執行...")
    ensure_header()
    update_sheet_data()
    print("程式結束。")
