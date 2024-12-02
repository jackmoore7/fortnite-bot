import pytz
import os
import requests

from datetime import datetime as dt

def get_arpansa_data():
    current_date = dt.now(pytz.timezone('Australia/Sydney')).strftime('%Y-%m-%d')
    url = os.getenv('ARPANSA_URL')
    r = requests.get(f"{url}&date={current_date}")
    return r.json()

def calculate_hex(num):
    color_mapping = {
        0: 0x78B159,
        3: 0xFDCB58,
        6: 0xF4900C,
        8: 0xDD2E44,
        11: 0xAA8ED6
    }
    closest_value = max(filter(lambda x: x <= float(num), color_mapping))
    return color_mapping.get(closest_value)

def calculate_emoji(num):
    emoji_mapping = {
        0: "🟢",
        3: "🟡",
        6: "🟠",
        8: "🔴",
        11: "🟣💀"
    }
    closest_value = max(filter(lambda x: x <= float(num), emoji_mapping))
    return emoji_mapping.get(closest_value)