import requests
import sqlite3 as sl
from time import sleep
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
        sleep(2)
        return get_fortnite_status()
    r = r.json()
    try:
        if r['message']:
            return r['message']
        elif r['errorCode']:
            return r['errorCode']
    except:
        print("Failed to get Fortnite status. Trying again in 1 minute.")
        sleep(60)
        return get_fortnite_status()

def get_fortnite_update_manifest(): #need to use the launcher client token
    url = "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/public/assets/v2/platform/Windows/namespace/fn/catalogItem/4fe75bbc5a674f4f9b356b5c90567da5/app/Fortnite/label/Live"
    key = cursor.execute("SELECT launcher FROM keys").fetchall()[0][0]
    r = requests.get(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401: #key expired, generate a new one. expires every 4 hours.
        x = dt.now().isoformat()
        print("New launcher token needed at " + str(x))
        get_account_key_launcherAppClient2()
        sleep(2)
        return get_fortnite_update_manifest()
    r = r.json()
    try:
        if r['elements'][0]['buildVersion']:
            return r['elements'][0]['buildVersion']
        elif r['errorCode']:
            return r['errorCode']
    except:
        print("Failed to get launcher manifest. Trying again in 1 minute.")
        sleep(60)
        return get_fortnite_update_manifest()

def get_fortnite_shop_offers():
    date = dt.utcnow().date()
    body = {
    "query":"query searchStoreQuery($allowCountries: String, $category: String, $count: Int, $country: String!, $keywords: String, $locale: String, $namespace: String, $itemNs: String, $sortBy: String, $sortDir: String, $start: Int, $tag: String, $releaseDate: String, $withPrice: Boolean = false, $withPromotions: Boolean = false, $priceRange: String, $freeGame: Boolean, $onSale: Boolean, $effectiveDate: String) {\n  Catalog {\n    searchStore(\n      allowCountries: $allowCountries\n      category: $category\n      count: $count\n      country: $country\n      keywords: $keywords\n      locale: $locale\n      namespace: $namespace\n      itemNs: $itemNs\n      sortBy: $sortBy\n      sortDir: $sortDir\n      releaseDate: $releaseDate\n      start: $start\n      tag: $tag\n      priceRange: $priceRange\n      freeGame: $freeGame\n      onSale: $onSale\n      effectiveDate: $effectiveDate\n    ) {\n      elements {\n       id\n        namespace\n      title\n      title4Sort\n                description\n       creationDate\n        viewableDate\n        releaseDate\n        pcReleaseDate\n        effectiveDate\n        expiryDate\n        lastModifiedDate\n        keyImages {\n          type\n          url\n          size\n          width\n          height\n          uploadedDate\n       }\n        seller {\n          id\n          name\n        }\n        productSlug\n          urlSlug\n        url\n        tags {\n          id\n        }\n        items {\n          id\n          namespace\n        }\n        customAttributes {\n          key\n          value\n        }\n        categories {\n          path\n        }\n        catalogNs {\n          mappings(pageType: \"productHome\") {\n            pageSlug\n            pageType\n          }\n        }\n        offerMappings {\n          pageSlug\n          pageType\n        }\n        developerDisplayName\n        publisherDisplayName\n        currentPrice\n        basePrice\n        price(country: $country) @include(if: $withPrice) {\n          totalPrice {\n            discountPrice\n            originalPrice\n            voucherDiscount\n            discount\n            currencyCode\n            currencyInfo {\n              decimals\n            }\n            fmtPrice(locale: $locale) {\n              originalPrice\n              discountPrice\n              intermediatePrice\n            }\n          }\n          lineOffers {\n            appliedRules {\n              id\n              endDate\n              discountSetting {\n                discountType\n              }\n            }\n          }\n        }\n        promotions(category: $category) @include(if: $withPromotions) {\n          promotionalOffers {\n            promotionalOffers {\n              startDate\n              endDate\n              discountSetting {\n                discountType\n                discountPercentage\n              }\n            }\n          }\n          upcomingPromotionalOffers {\n            promotionalOffers {\n              startDate\n              endDate\n              discountSetting {\n                discountType\n                discountPercentage\n              }\n            }\n          }\n        }\n      }\n      paging {\n        count\n        total\n      }\n    }\n  }\n}\n",
   "variables":{
      "category":"digitalextras/book|addons|digitalextras/soundtrack|digitalextras/video",
      "count": 100,
      "country":"AU",
      "keywords":"",
      "locale":"en",
      "namespace":"fn",
      "sortBy":"releaseDate",
      "sortDir":"DESC",
      "allowCountries":"AU",
      "start":0,
      "tag":"",
      "releaseDate":f"[,{date}]",
      "withPrice":True
        }
    }
    r = requests.post("https://www.epicgames.com/graphql?operationName=searchStoreQuery", json=body)
    try:
        r = r.json()
        r = r['data']['Catalog']['searchStore']['elements']
        return r
    except:
        print("Failed to get Fortnite shop offers. Trying again in 1 minute.")
        sleep(60)
        return get_fortnite_shop_offers()

def get_fortnite_shop1():
    url = "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/storefront/v2/catalog"
    key = cursor.execute("SELECT switch FROM keys").fetchone()[0]
    r = requests.get(url, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401:
        x = dt.now().isoformat()
        print("New device auth token needed at " + str(x))
        get_device_auth_2()
        sleep(2)
        return get_fortnite_shop1()
    return r.json()

def get_fortnite_shop_item_details(id):
    url = "https://catalog-public-service-prod06.ol.epicgames.com/catalog/api/shared/bulk/offers?returnItemDetails=True"
    key = cursor.execute("SELECT switch FROM keys").fetchone()[0]
    params = {
        'id': id,
		'country': "AU",
		'locale': "EN"
    }
    r = requests.get(url, params=params, headers={"Content-Type":"application/x-www-form-urlencoded", "Authorization":"Bearer " + key})
    if r.status_code == 401:
        x = dt.now().isoformat()
        print("New device auth token needed at " + str(x))
        get_device_auth_2()
        sleep(2)
        return get_fortnite_shop_item_details(id)
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
        sleep(2)
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
        sleep(2)
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
        sleep(2)
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
        sleep(2)
        return get_user_presence()
    try:
        if r.json()[user_id]:
            return r.json()[user_id][0]['last_online']
    except Exception as e:
        return None
    
def get_free_games():
    url = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=AU&allowCountries=AU"
    r = requests.get(url)
    if r.status_code == 200:
        r = r.json()
        games_list = []
        games = r['data']['Catalog']['searchStore']['elements']
        for game in games:
            if len(game['promotions']['promotionalOffers']) > 0:
                if game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]:
                    title = game['title']
                    description = game['description']
                    image_url = [item["url"] for item in game["keyImages"] if item["type"] == "DieselStoreFrontWide"]
                    start_date = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['startDate']
                    end_date = game['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['endDate']
                    games_list.append((title, description, image_url[0], start_date, end_date))
            return games_list
    else:
        return None