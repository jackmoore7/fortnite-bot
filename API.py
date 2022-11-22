import requests
import os
import re
import uuid
import shutil

def fortnite_br_stats(username):
	url = "https://fortnite-api.com/v2/stats/br/v2"
	key = os.getenv('FNAPI_COM_KEY')
	r = requests.get(url, params={"name": username}, headers={"Authorization": key})
	return r

def getAccountID(username):
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
	accountId = getAccountID(username)
	if accountId == "no":
		return "no"
	r = requests.get(url, params={"accountId": accountId}, headers={"Authorization": key})
	if r.status_code != 200:
		print("Failed to fetch user fish data")
		return 404
	return r.json()

def daily_shop():
	return urls