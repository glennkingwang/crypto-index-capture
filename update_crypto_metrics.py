import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# --- Google Sheets 設置 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ").sheet1

# --- 標題行 ---
HEADER_ROW = ["Date", "CFGI", "BTC-D", "Long/Short", "Open Interest", "Funding Rate", "Exec Time"]

# --- API 函數 ---

def fetch_cfgi():
    """恐懼與貪婪指數"""
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        r.raise_for_status()
        data = r.json().get('data')
        if data and len(data) > 0:
            return int(data[0]['value'])
        else:
            print("Error fetch_cfgi: API returned empty or invalid data.")
            return None
    except Exception as e:
        print(f"Error in fetch_cfgi: {e}")
        return None

def fetch_btc_d():
    """BTC 市佔率 (CoinGecko)"""
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
        r.raise_for_status()
        btc_percentage = r.json().get('data', {}).get('market_cap_percentage', {}).get('btc')
        if btc_percentage is not None:
            return round(btc_percentage, 2)
        else:
            print("Error fetch_btc_d: Could not parse BTC dominance.")
            return None
    except Exception as e:
        print(f"Error in fetch_btc_d: {e}")
        return None

def fetch_long_short_ratio():
    """多空比 (Binance Futures)"""
    try:
        time.sleep(1)
        r = requests.get(
            "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1",
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return round(float(data[0]['longShortRatio']), 2)
        else:
            print("Error fetch_long_short_ratio: Response =", data)
            return None
    except Exception as e:
        print(f"Error in fetch_long_short_ratio: {e}")
        return None

def fetch_open_interest():
    """未平倉量 (Binance Futures)"""
    try:
        time.sleep(1)
        r = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT", timeout=10)
        r.raise_for_status()
        data = r.json()
        if 'openInterest' in data:
            return round(float(data['openInterest']), 2)
        else:
            print("Error fetch_open_interest: Response =", data)
            return None
    except Exception as e:
        print(f"Error in fetch_open_interest: {e}")
        return None

def fetch_funding_rate():
    """資金費率 (Binance Futures)"""
    try:
        time.sleep(1)
        r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1", timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return round(float(data[0]['fundingRate']) * 100, 4)
        else:
            print("Error fetch_funding_rate: Response =", data)
            return None
    except Exception as e:
        print(f"Error in fetch_funding_rate: {e}")
        return None

# --- 更新 Google Sheet ---
def update_sheet_data():
    now = datetime.utcnow()
    today_date = now.strftime("%Y-%m-%d")
    exec_time = now.strftime("%H:%M:%S (UTC)")

    print(f"Fetching data at {exec_time}...")

    row = [
        today_date,
        fetch_cfgi(),
        fetch_btc_d(),
        fetch_long_short_ratio(),
        fetch_open_interest(),
        fetch_funding_rate(),
        exec_time
    ]

    try:
        sheet.append_row(row)
        print(f"--- {today_date} metrics updated successfully ---")
        print(f"Data: {row}")
    except Exception as e:
        print(f"Error: Failed to append row. Error: {e}")
        print(f"Data that failed: {row}")

# --- 主程式 ---
if __name__ == "__main__":
    try:
        current_header = sheet.row_values(1)
        if current_header != HEADER_ROW:
            print("Header not found or incorrect. Inserting new header...")
            sheet.insert_row(HEADER_ROW, 1)
            print("Header inserted.")
        else:
            print("Header is correct. Skipping insertion.")
    except Exception as e:
        print("Error checking header:", e)
        sheet.insert_row(HEADER_ROW, 1)

    update_sheet_data()
