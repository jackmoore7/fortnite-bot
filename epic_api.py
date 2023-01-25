import requests
import sqlite3 as sl
import time
import os
from datetime import datetime as dt

from key_handling import *

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

def get_fortnite_status(): #need to use the fortnite client token
    url = "https://lightswitch-public-service-prod.ol.epicgames.com/lightswitch/api/service/fortnite/status"
    key = cursor.execute("SELECT fortnite FROM keys").fetchall()[0][0]
    r = requests.get(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401: #key expired, generate a new one. expires every 4 hours.
        x = dt.now().isoformat()
        print("New Fortnite client token needed at " + str(x))
        get_account_key_fortnitePCGameClient()
        time.sleep(2)
        return get_fortnite_status()
    r = r.json()
    try:
        if r['message']:
            return r['message']
        elif r['errorCode']:
            return r['errorCode']
    except:
        print("Failed to get Fortnite status. No message or error code")
        return None

def get_fortnite_update_manifest(): #need to use the launcher client token
    url = "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/public/assets/v2/platform/Windows/namespace/fn/catalogItem/4fe75bbc5a674f4f9b356b5c90567da5/app/Fortnite/label/Live"
    key = cursor.execute("SELECT launcher FROM keys").fetchall()[0][0]
    r = requests.get(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401: #key expired, generate a new one. expires every 4 hours.
        x = dt.now().isoformat()
        print("New launcher token needed at " + str(x))
        get_account_key_launcherAppClient2()
        time.sleep(2)
        return get_fortnite_update_manifest()
    r = r.json()
    try:
        if r['elements'][0]['buildVersion']:
            return r['elements'][0]['buildVersion']
        elif r['errorCode']:
            return r['errorCode']
    except:
        print("Failed to get launcher manifest")
        return None

def get_fortnite_shop1():
    url = "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/storefront/v2/catalog?rvn=5479"
    key = cursor.execute("SELECT switch FROM keys").fetchone()[0]
    r = requests.get(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401:
        x = dt.now().isoformat()
        print("New device auth token needed at " + str(x))
        get_device_auth_2()
        time.sleep(2)
        return get_fortnite_shop1()
    return r.json()

def add_friend(user_id):
    client_id = os.getenv('CLIENT_ID')
    key = cursor.execute("SELECT switch FROM keys").fetchone()[0]
    url = f"https://friends-public-service-prod.ol.epicgames.com/friends/api/v1/{client_id}/friends/{user_id}"
    r = requests.post(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401:
        x = dt.now().isoformat()
        print("New device auth token needed at " + str(x))
        get_device_auth_2()
        time.sleep(2)
        return add_friend(user_id)
    return r.json()

def get_all_friends(include_pending: bool = False):
    params = {
        'includePending': include_pending
    }
    client_id = os.getenv('CLIENT_ID')
    key = cursor.execute("SELECT switch FROM keys").fetchone()[0]
    url = f"https://friends-public-service-prod.ol.epicgames.com/friends/api/public/friends/{client_id}"
    r = requests.get(url, params=params, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401:
        x = dt.now().isoformat()
        print("New device auth token needed at " + str(x))
        get_device_auth_2()
        time.sleep(2)
        return get_all_friends()
    return r.json()

def get_user_by_id(user_id):
    key = cursor.execute("SELECT switch FROM keys").fetchone()[0]
    url = f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{user_id}"
    r = requests.get(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401:
        x = dt.now().isoformat()
        print("New device auth token needed at " + str(x))
        get_device_auth_2()
        time.sleep(2)
        return get_user_by_id(user_id)
    return r.json()

def get_user_presence(user_id):
    key = cursor.execute("SELECT switch FROM keys").fetchone()[0]
    client_id = os.getenv('CLIENT_ID')
    url = f"https://presence-public-service-prod.ol.epicgames.com/presence/api/v1/_/{client_id}/last-online"
    r = requests.get(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401:
        x = dt.now().isoformat()
        print("New device auth token needed at " + str(x))
        get_device_auth_2()
        time.sleep(2)
        return get_user_presence()
    try:
        if r.json()[user_id]:
            return r.json()[user_id][0]['last_online']
    except Exception as e:
        return None