import requests
import os
from datetime import datetime as dt, timedelta
from imports.core_utils import cursor
from dotenv import load_dotenv

load_dotenv()
uname = os.getenv("TFNSW_USERNAME")
pwd = os.getenv("TFNSW_PASSWORD")
today_d = dt.today().strftime('%Y-%m-%d')
seven_d = (dt.today() - timedelta(days=7)).strftime('%Y-%m-%d')

session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json"
})

def login(session, username, password):
    url = "https://transportnsw.info/api/opal/login"
    payload = {
        "username": username,
        "password": password,
        "grant_type": "password"
    }
    try:
        response = session.post(url, json=payload)
        if response.status_code == 200:
            token = response.json().get('access_token').strip()
            cursor.execute("UPDATE tfnsw_access_token SET token = ?", (token,))
            print(f"New token is: {token}")
            return token
        else:
            print(f"Login failed with status {response.status_code}: {response.text}")
            return f"Login failed with status {response.status_code}: {response.text}"
    except requests.exceptions.RequestException as e:
        print(f"Login request failed: {e}")
        return f"Login request failed: {e}"

def get_token():
    token = cursor.execute("SELECT token FROM tfnsw_access_token").fetchone()
    if token:
        return token[0]
    else:
        print("No token found in the database. Please login.")
        return "No token found in the database. Please login."

def refresh_token():
    print("Refreshing token...")
    return login(session, uname, pwd)

def handle_response(response):
    if response.status_code in [401, 500]:
        print(f"Error {response.status_code}: {response.text}")
        return f"Error {response.status_code}: {response.text}"
    elif response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            print("Failed to parse JSON response.")
            return "Failed to parse JSON response."
    else:
        print(f"Unexpected status code {response.status_code}: {response.text}")
        return f"Unexpected status code {response.status_code}: {response.text}"

def get_cards():
    token = get_token()
    if not token:
        token = refresh_token()
        if not token:
            return "Failed to obtain token."

    url = "https://transportnsw.info/api/opal/api/customer/smartcards/"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print(f"Trying to get cards with token: {token}")
    try:
        response = session.get(url, headers=headers)
        result = handle_response(response)
        if response.status_code == 401 or response.status_code == 500:
            token = refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                response = session.get(url, headers=headers)
                result = handle_response(response)
        return result
    except requests.exceptions.RequestException as e:
        print(f"Failed to get cards: {e}")
        return f"Failed to get cards: {e}"

def top_up(card_id, cents):
    token = get_token()
    if not token:
        token = refresh_token()
        if not token:
            return "Failed to obtain token."

    url = "https://transportnsw.info/api/opal/api/smartcard/topup/"
    payload = {
        "SmartcardId": int(card_id),
        "TopupValue": int(cents)
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print(f"Trying to top up card {card_id} with token: {token}")
    try:
        response = session.post(url, json=payload, headers=headers)
        result = handle_response(response)
        if response.status_code == 401 or response.status_code == 500:
            token = refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                response = session.post(url, json=payload, headers=headers)
                result = handle_response(response)
        return result
    except requests.exceptions.RequestException as e:
        print(f"Failed to top up: {e}")
        return f"Failed to top up: {e}"

def get_trip_history(card_id):
    token = get_token()
    if not token:
        token = refresh_token()
        if not token:
            return "Failed to obtain token."

    url = f"https://transportnsw.info/api/opal/api/smartcard/activity/{card_id}"
    params = {
        "start": 0,
        "nr": 500,
        "from": seven_d,
        "to": today_d,
        "sort": ""
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print(f"Trying to get trip history for card {card_id} with token: {token}")
    try:
        response = session.get(url, headers=headers, params=params)
        result = handle_response(response)
        if response.status_code == 401 or response.status_code == 500:
            token = refresh_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                response = session.get(url, headers=headers, params=params)
                result = handle_response(response)
        return result
    except requests.exceptions.RequestException as e:
        print(f"Failed to get trip history: {e}")
        return f"Failed to get trip history: {e}"
