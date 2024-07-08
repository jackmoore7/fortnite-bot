import requests
import os

def fortnite_br_stats(username):
	url = "https://fortnite-api.com/v2/stats/br/v2"
	key = os.getenv('FNAPI_COM_KEY')
	r = requests.get(url, params={"name": username}, headers={"Authorization": key})
	return r

def get_account_id(username):
	url = "https://fortniteapi.io/v1/lookup"
	key = os.getenv('FNAPI_IO_KEY')
	r = requests.get(url, params={"username": username}, headers={"Authorization": key})
	if r.json()['result'] != False:
		return(r.json()['account_id'])
	else:
		return "no"

def fish_loot_pool():
	url = "https://fortniteapi.io/v1/loot/fish?lang=en"
	key = os.getenv('FNAPI_IO_KEY')
	r = requests.get(url, headers={"Authorization": key})
	return r.json()

def fish_stats(username):
	url = "https://fortniteapi.io/v1/stats/fish"
	key = os.getenv('FNAPI_IO_KEY')
	account_id = get_account_id(username)
	if account_id == "no":
		return "no"
	r = requests.get(url, params={"accountId": account_id}, headers={"Authorization": key})
	if r.status_code != 200:
		print("Failed to fetch user fish data")
		return 404
	return r.json()

def fortnite_augments():
	url = "https://fortniteapi.io/v1/game/augments"
	key = os.getenv('FNAPI_IO_KEY')
	r = requests.get(url, headers={"Authorization": key})
	return r.json()

def fortnite_shop_v3():
	url = "https://fnbr.co/api/shop"
	key = os.getenv('FNBR_API_KEY')
	r = requests.get(url, headers={"x-api-key": key})
	return r.json()

def fortnite_images(name):
	try:
		url = f"https://fnbr.co/api/images?search={name}"
		key = os.getenv('FNBR_API_KEY')
		r = requests.get(url, headers={"x-api-key": key})
		return r.json()['data'][0]['images']['icon']
	except Exception:
		return None