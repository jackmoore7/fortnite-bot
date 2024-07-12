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
	r = requests.get(url, headers=headers, verify=False)
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
	r = requests.get(url + build_version + "/en/search.json?q=" + query, headers=headers, verify=False)
	if r.status_code == 404:
		update_build_number()
		build_version = cursor.execute(select_coles_version).fetchone()[0]
		r = requests.get(url + build_version + "/en/search.json?q=" + query, headers=headers, verify=False)
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
	r = requests.post(url, headers=headers, json=payload, verify=False)
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