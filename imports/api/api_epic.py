import os
import requests

from time import sleep

from imports.key_handling import *

from imports.core_utils import cursor

content_type = "application/x-www-form-urlencoded"
select_switch = "SELECT switch FROM keys"
bearer = "Bearer "

def get_fortnite_status(): #need to use the fortnite client token
    url = "https://lightswitch-public-service-prod.ol.epicgames.com/lightswitch/api/service/fortnite/status"
    key = cursor.execute("SELECT fortnite FROM keys").fetchall()[0][0]
    auth = bearer + key
    r = requests.get(url, headers={"Content-Type":content_type, "Authorization":auth})
    if r.status_code == 401: #key expired, generate a new one. expires every 4 hours.
        # x = dt.now().isoformat()
        get_account_key_fortnite_pc_game_client()
        sleep(2)
        return get_fortnite_status()
    r = r.json()
    if r['message']:
        return r['message']
    elif r['errorCode']:
        return r['errorCode']

def get_fortnite_update_manifest(): #need to use the launcher client token
    url = "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/public/assets/v2/platform/Windows/namespace/fn/catalogItem/4fe75bbc5a674f4f9b356b5c90567da5/app/Fortnite/label/Live"
    key = cursor.execute("SELECT launcher FROM keys").fetchall()[0][0]
    auth = bearer + key
    r = requests.get(url, headers={"Content-Type":content_type, "Authorization":auth})
    if r.status_code == 401: #key expired, generate a new one. expires every 4 hours.
        # x = dt.now().isoformat()
        get_account_key_launcher_app_client_2()
        sleep(2)
        return get_fortnite_update_manifest()
    r = r.json()
    if r['elements'][0]['buildVersion']:
        return r['elements'][0]['buildVersion']
    elif r['errorCode']:
        return r['errorCode']

def get_fortnite_shop_item_details(id):
    url = "https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/bulk/offers?returnItemDetails=True"
    key = cursor.execute(select_switch).fetchone()[0]
    auth = bearer + key
    params = {
        'id': id,
		'country': "AU",
		'locale': "EN"
    }
    r = requests.get(url, params=params, headers={"Content-Type":content_type, "Authorization":auth})
    if r.status_code == 401:
        # x = dt.now().isoformat()
        get_device_auth_2()
        sleep(2)
        return get_fortnite_shop_item_details(id)
    return r.json()

def add_friend(user_id):
    client_id = os.getenv('CLIENT_ID')
    url = f"https://friends-public-service-prod.ol.epicgames.com/friends/api/v1/{client_id}/friends/{user_id}"
    key = cursor.execute(select_switch).fetchone()[0]
    auth = bearer + key
    r = requests.post(url, headers={"Content-Type":content_type, "Authorization":auth})
    if r.status_code == 401:
        # x = dt.now().isoformat()
        get_device_auth_2()
        sleep(2)
        return add_friend(user_id)
    return r.json()

def get_all_friends(include_pending: bool = False):
    client_id = os.getenv('CLIENT_ID')
    url = f"https://friends-public-service-prod.ol.epicgames.com/friends/api/public/friends/{client_id}"
    key = cursor.execute(select_switch).fetchone()[0]
    auth = bearer + key
    params = {
        'includePending': include_pending
    }
    r = requests.get(url, params=params, headers={"Content-Type":content_type, "Authorization":auth})
    if r.status_code == 401:
        # x = dt.now().isoformat()
        get_device_auth_2()
        sleep(2)
        return get_all_friends(include_pending)
    return r.json()

def get_user_by_id(user_id):
    url = f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{user_id}"
    key = cursor.execute(select_switch).fetchone()[0]
    auth = bearer + key
    r = requests.get(url, headers={"Content-Type":content_type, "Authorization":auth})
    if r.status_code == 401:
        # x = dt.now().isoformat()
        get_device_auth_2()
        sleep(2)
        return get_user_by_id(user_id)
    return r.json()

def get_user_presence(user_id):
    client_id = os.getenv('CLIENT_ID')
    url = f"https://presence-public-service-prod.ol.epicgames.com/presence/api/v1/_/{client_id}/last-online"
    key = cursor.execute(select_switch).fetchone()[0]
    auth = bearer + key
    r = requests.get(url, headers={"Content-Type":content_type, "Authorization":auth})
    if r.status_code == 401:
        # x = dt.now().isoformat()
        get_device_auth_2()
        sleep(2)
        return get_user_presence(user_id)
    try:
        if r.json()[user_id]:
            return r.json()[user_id][0]['last_online']
    except Exception:
        return None
    
def get_free_games():
    url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=AU&allowCountries=AU"
    r = requests.get(url)
    if r.status_code == 200:
        r = r.json()
        games_list = []
        games = r['data']['Catalog']['searchStore']['elements']
        for game in games:
            if game.get('promotions') and game['promotions'].get('promotionalOffers'):
                if game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]:
                    title = game['title']
                    description = game['description']
                    image_url = [item["url"] for item in game["keyImages"] if "wide" in item["type"].lower()]
                    start_date = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['startDate']
                    end_date = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['endDate']
                    games_list.append((title, description, image_url[0], start_date, end_date))
        return games_list
    else:
        return None

def get_fortnite_maintenance():
    try:
        url = "https://status.epicgames.com/api/v2/scheduled-maintenances.json"
        response = requests.get(url).json()
        return response.get("scheduled_maintenances", [])
    except Exception as e:
        print(f"Error fetching maintenance: {repr(e)}")
        return []
