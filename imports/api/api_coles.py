import json
import urllib.parse
import requests

from bs4 import BeautifulSoup
from imports.core_utils import cursor

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
select_coles_version = "SELECT version FROM coles_version"

def update_build_number():
	build_version = cursor.execute(select_coles_version).fetchone()[0]
	url = "https://www.coles.com.au/_next/data/"
	r = requests.get(url, headers=headers)
	soup = BeautifulSoup(r.content, 'html.parser')
	script = soup.find("script", id="__NEXT_DATA__")
	if script:
		json_data = json.loads(script.string)
		build_id = json_data['buildId']
		if build_id != build_version:
			cursor.execute("UPDATE coles_version SET version = ?", (build_id,))
			print(f"Coles API version number was updated to {build_id}")
	
def search_item(query):
	query = urllib.parse.quote(query)
	build_version = cursor.execute(select_coles_version).fetchone()[0]
	url = "https://www.coles.com.au/_next/data/"
	r = requests.get(url + build_version + "/en/search/products.json?q=" + query, headers=headers)
	if r.status_code == 404:
		update_build_number()
		build_version = cursor.execute(select_coles_version).fetchone()[0]
		r = requests.get(url + build_version + "/en/search/products.json?q=" + query, headers=headers)
		if r.status_code == 404:
			return "Your search returned a 404"
	r = r.json()
	results = r['pageProps']['searchResults']
	return results

def get_items(id_list):
	item_list = []
	ids_string = ",".join(map(str, id_list))
	payload = {"productIds":ids_string}
	url = "https://coles.com.au/api/products"
	r = requests.post(url, headers=headers, json=payload)
	if r.status_code == 500:
		r = r.json()
		print(f"An error occurred for {id_list}. Trying each item individually.")
		if len(id_list) == 1:
			cursor.execute("INSERT INTO coles_error_ids (id) VALUES (?)", (id_list[0],))
			cursor.execute("DELETE FROM coles_active_ids WHERE id = ?", (id_list[0],))
			print(f"{id_list[0]} is a bad boy and was added to the error IDs database and deleted from the active IDs database.")
			return
		new_item_list = []
		new_invalid_ids_list = []
		for item in id_list:
			print(f"Trying {item}")
			response = get_items([item])
			if response:
				if len(response['invalid_ids']) > 0:
					new_invalid_ids_list.append(response['invalid_ids'][0])
				else:
					new_item_list.extend(response['items'])
		data = {
			"invalid_ids": new_invalid_ids_list,
			"items": new_item_list
		}
		return data
	r = r.json()
	for item in r['results']:
		item_id = item['id']
		name = item['name']
		brand = item['brand']
		description = item['description']
		image_url = "https://productimages.coles.com.au/productimages" + item['imageUris'][0]['uri']
		try:
			current_price = item['pricing']['now']
		except:
			current_price = None
		if item.get('pricing') and item['pricing'].get('promotionType'):
			on_sale = True
			promotion_type = item['pricing']['promotionType']
		else:
			on_sale = False
			promotion_type = ""
		try:
			available = item['availability']
		except:
			available = None
		if item.get('pricing') and item['pricing'].get('offerDescription'):
			offer_description = item['pricing']['offerDescription']
		else:
			offer_description = ""
		if item.get('pricing') and item['pricing'].get('multiBuyPromotion'):
			multibuy_unit_price = item['pricing']['multiBuyPromotion']['reward']
		else:
			multibuy_unit_price = ""
		item_list.append([item_id, name, brand, description, current_price, on_sale, available, offer_description, multibuy_unit_price, image_url, promotion_type])
	data = {
		"invalid_ids": r['invalidProducts'],
		"items": item_list
	}
	return data

def try_bad_boys():
	error_ids = cursor.execute("SELECT id FROM coles_error_ids").fetchall()
	error_ids = [x[0] for x in error_ids]
	url = "https://coles.com.au/api/products"
	for item in error_ids:
		payload = {"productIds":str(item)}
		r = requests.post(url, headers=headers, json=payload)
		if r.status_code != 500:
			cursor.execute("INSERT INTO coles_active_ids (id) VALUES (?)", (item,))
			cursor.execute("DELETE FROM coles_error_ids WHERE id = ?", (item,))
			print(f"{item} is no longer throwing an error and was added to the active IDs database.")
