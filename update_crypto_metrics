import requests
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1XRLTnE56zLPVf__AwQfXvJ5FOkmt9fegjbpwaPhYuSQ").sheet1

def fetch_cfgi():
    r = requests.get("https://api.alternative.me/fng/")
    return int(r.json()['data'][0]['value'])

def fetch_btc_d():
    r = requests.get("https://api.coingecko.com/api/v3/global")
    return round(r.json()['data']['market_cap_percentage']['btc'], 2)

def fetch_long_short_ratio():
    r = requests.get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1d&limit=1")
    return round(float(r.json()[0]['longShortRatio']), 2)

def fetch_open_interest():
    r = requests.get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT")
    return round(float(r.json()['openInterest']), 2)

def fetch_funding_rate():
    r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1")
    return round(float(r.json()[0]['fundingRate']) * 100, 4)

def update_sheet():
    today = datetime.now().strftime("%Y-%m-%d")
    row = [
        today,
        fetch_cfgi(),
        fetch_btc_d(),
        fetch_long_short_ratio(),
        fetch_open_interest(),
        fetch_funding_rate()
    ]
    sheet.append_row(row)
    print(f"{today} 指標已更新")

if __name__ == "__main__":
    update_sheet()
