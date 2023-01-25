import requests
import sqlite3 as sl
import os

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

def get_account_key_fortnitePCGameClient():
    url = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
    username = os.getenv('GAMECLIENT_USERNAME')
    password = os.getenv('GAMECLIENT_PASSWORD')
    r = requests.post(url, headers={"Content-Type":"application/x-www-form-urlencoded"}, data={"grant_type":"client_credentials"}, auth=(username, password))
    r = r.json()
    try:
        if r['access_token']:
            print("Fortnite client token generated successfully.")
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
            cursor.execute("UPDATE keys SET launcher = ?", (r['access_token'],))
            return r['access_token']
    except:
        print("Failed to generate a new launcher client token.")
        return None

def get_device_auth_2():
    url = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
    r = requests.post(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"basic " + os.getenv('DEVICE_AUTH')}, data={"grant_type":"device_auth", "account_id":os.getenv('DA_ACCOUNT_ID'), "device_id":os.getenv('DA_DEVICE_ID'), "secret":os.getenv('DA_SECRET')})
    r = r.json()
    try:
        if r['access_token']:
            print("Device auth token generated successfully.")
            cursor.execute("UPDATE keys SET switch = ?", (r['access_token'],))
            return r['access_token']
    except:
        print("Failed to generate a new device auth token.")
        return None