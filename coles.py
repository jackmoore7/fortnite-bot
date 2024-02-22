import requests
import sqlite3 as sl
from bs4 import BeautifulSoup
import json
import urllib.parse

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

def update_build_number():
    build_version = cursor.execute("SELECT version FROM coles_version").fetchone()[0]
    url = "https://www.coles.com.au/_next/data/"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    script = soup.find("script", id="__NEXT_DATA__")
    if script:
        json_data = json.loads(script.string)
        build_id = json_data['buildId']
        if build_id != build_version:
            cursor.execute("UPDATE coles_version SET version = ?", (build_id,))
            print(f"Coles API version number was updated to {build_id}")
    
def get_item_by_id(id):
    build_version = cursor.execute("SELECT version FROM coles_version").fetchone()[0]
    url = "https://www.coles.com.au/_next/data/"
    r = requests.get(url + build_version + "/en/product/" + str(id) + ".json")
    if r.status_code == 404:
        update_build_number()
        build_version = cursor.execute("SELECT version FROM coles_version").fetchone()[0]
        r = requests.get(url + build_version + "/en/product/" + str(id) + ".json")
        if r.status_code == 404:
            return f"{id} returned a 404. Build number does not need updating."
    r = r.json()
    product = r['pageProps']['__N_REDIRECT']
    r = requests.get(url + build_version + "/en" + product + ".json")
    r = r.json()
    id = r['pageProps']['product']['id']
    name = r['pageProps']['product']['name']
    brand = r['pageProps']['product']['brand']
    description = r['pageProps']['product']['description']
    image_url = "https://productimages.coles.com.au/productimages" + r['pageProps']['product']['imageUris'][0]['uri']
    try:
        current_price = r['pageProps']['product']['pricing']['now']
    except TypeError:
        current_price = None
    if r.get('pageProps') and r['pageProps'].get('product') and r['pageProps']['product'].get('pricing') and r['pageProps']['product']['pricing'].get('promotionType'):
        on_sale = True
    else:
        on_sale = False
    available = r['pageProps']['product']['availability']
    if r.get('pageProps') and r['pageProps'].get('product') and r['pageProps']['product'].get('pricing') and r['pageProps']['product']['pricing'].get('offerDescription'):
        offer_description = r['pageProps']['product']['pricing']['offerDescription']
    else:
        offer_description = ""
    if r.get('pageProps') and r['pageProps'].get('product') and r['pageProps']['product'].get('pricing') and r['pageProps']['product']['pricing'].get('multiBuyPromotion'):
        multibuy_unit_price = r['pageProps']['product']['pricing']['multiBuyPromotion']['reward']
    else:
        multibuy_unit_price = ""
    return (id, name, brand, description, current_price, on_sale, available, offer_description, multibuy_unit_price, image_url)
    
def search_item(query):
    query = urllib.parse.quote(query)
    build_version = cursor.execute("SELECT version FROM coles_version").fetchone()[0]
    url = "https://www.coles.com.au/_next/data/"
    r = requests.get(url + build_version + "/en/search.json?q=" + query)
    if r.status_code == 404:
        update_build_number()
        build_version = cursor.execute("SELECT version FROM coles_version").fetchone()[0]
        r = requests.get(url + build_version + "/en/search.json?q=" + query)
        if r.status_code == 404:
            return "Your search returned a 404"
    r = r.json()
    results = r['pageProps']['searchResults']
    return results