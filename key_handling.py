import requests
import sqlite3 as sl
import time
import os
from datetime import datetime as dt

def get_account_key_fortnitePCGameClient():
    url = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
    username = os.getenv('GAMECLIENT_USERNAME')
    password = os.getenv('GAMECLIENT_PASSWORD')
    r = requests.post(url, headers={"Content-Type":"application/x-www-form-urlencoded"}, data={"grant_type":"client_credentials"}, auth=(username, password))
    r = r.json()
    try:
        if r['access_token']:
            print("Fortnite client token generated successfully.")
            con = sl.connect('fortnite.db', isolation_level=None)
            cursor = con.cursor()
            cursor.execute("UPDATE keys SET fortnite = ?", (r['access_token'],))
            return r['access_token']
    except:
        print("Failed to generate a new Fortnite client token.")
        return None


def get_account_key_launcherAppClient2():
    url = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
    username = os.getenv('LAUNCHERCLIENT_USERNAME')
    password = os.getenv('LAUNCHERCLIENT_PASSWORD')
    r = requests.post(url, headers={"Content-Type":"application/x-www-form-urlencoded"}, data={"grant_type":"client_credentials"}, auth=(username, password))
    r = r.json()
    try:
        if r['access_token']:
            print("Launcher client token generated successfully.")
            con = sl.connect('fortnite.db', isolation_level=None)
            cursor = con.cursor()
            cursor.execute("UPDATE keys SET launcher = ?", (r['access_token'],))
            return r['access_token']
    except:
        print("Failed to generate a new launcher client token.")
        return None

def get_fortnite_status(): #need to use the fortnite client token
    url = "https://lightswitch-public-service-prod.ol.epicgames.com/lightswitch/api/service/fortnite/status"
    con = sl.connect('fortnite.db', isolation_level=None)
    cursor = con.cursor()
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
    con = sl.connect('fortnite.db', isolation_level=None)
    cursor = con.cursor()
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