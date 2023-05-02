import requests
import sqlite3 as sl
from bs4 import BeautifulSoup
import json
import urllib.parse

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()
    
def get_item_by_id(id):
    build_version = cursor.execute("SELECT version FROM coles_version").fetchone()[0]
    url = "https://www.coles.com.au/_next/data/"
    r = requests.get(url + build_version + "/en/product/" + str(id) + ".json")
    if r.status_code == 404:
        # build number may have changed, get the new one
        soup = BeautifulSoup(r.content, 'html.parser')
        script = soup.find("script", id="__NEXT_DATA__")
        if script:
            json_data = json.loads(script.string)
            build_id = json_data['buildId']
            if build_id != build_version:
                cursor.execute("UPDATE coles_version SET version = ?", (build_id,))
                print(f"Coles API version number was updated to {build_id}")
                return get_item_by_id(id)
            else:
                return "nah"
    else:
        r = r.json()
        product = r['pageProps']['__N_REDIRECT']
        r = requests.get(url + build_version + "/en" + product + ".json")
        r = r.json()
        id = r['pageProps']['product']['id']
        name = r['pageProps']['product']['name']
        brand = r['pageProps']['product']['brand']
        description = r['pageProps']['product']['description']
        try:
            current_price = r['pageProps']['product']['pricing']['now']
        except TypeError:
            current_price = None
        if r.get('pageProps') and r['pageProps'].get('product') and r['pageProps']['product'].get('pricing') and r['pageProps']['product']['pricing'].get('promotionType'):
            on_sale = True
        else:
            on_sale = False
        available = r['pageProps']['product']['availability']
        return (id, name, brand, description, current_price, on_sale, available)
    
def search_item(query):
    query = urllib.parse.quote(query)
    build_version = cursor.execute("SELECT version FROM coles_version").fetchone()[0]
    url = "https://www.coles.com.au/_next/data/"
    r = requests.get(url + build_version + "/en/search.json?q=" + query)
    r = r.json()
    results = r['pageProps']['searchResults']['results']
    results_amount = r['pageProps']['searchResults']['noOfResults']
    results_list = [(product['id'], product['name'], product['brand']) for product in results if ('adId' not in product or not product['adId']) and 'id' in product]
    results_list.insert(0, results_amount)
    return results_list


def add_item_to_db_by_id(id):
    product = get_item_by_id(id)
    id = product[0]
    name = product[1]
    brand = product[2]
    description = product[3]
    current_price = product[4]
    on_sale = product[5]
    available = product[6]
    item = cursor.execute("SELECT * FROM coles_specials WHERE id = ?", (id,)).fetchone()
    if item:
        return f"You're already tracking {brand} {name}"
    else:
        cursor.execute("INSERT INTO coles_specials VALUES (?, ?, ?, ?, ?, ?, ?)", (id, name, brand, description, current_price, on_sale, available))
        return f"Added {brand} {name} to your list"