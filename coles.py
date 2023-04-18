import requests
import sqlite3 as sl

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

def add_item_to_db_by_id(id):
    url = "https://www.coles.com.au/_next/data/20230404.03_v3.31.0/en"
    r = requests.get(url + "/product/" + id + ".json")
    r = r.json()
    product = r['pageProps']['__N_REDIRECT']
    r = requests.get(url + product + ".json")
    r = r.json()
    id = r['pageProps']['product']['id']
    name = r['pageProps']['product']['name']
    brand = r['pageProps']['product']['brand']
    description = r['pageProps']['product']['description']
    current_price = r['pageProps']['product']['pricing']['now']

    if r.get('pageProps') and r['pageProps'].get('product') and r['pageProps']['product'].get('pricing') and r['pageProps']['product']['pricing'].get('promotionType'):
        on_sale = True
    else:
        on_sale = False

    item = cursor.execute("SELECT * FROM coles_specials WHERE id = ?", (id,)).fetchone()
    if item:
        return f"You're already tracking {brand} {name}"
    else:
        cursor.execute("INSERT INTO coles_specials VALUES (?, ?, ?, ?, ?, ?)", (id, name, brand, description, current_price, on_sale))
        return f"Added {brand} {name} to your list"
    
def get_item_by_id(id):
    url = "https://www.coles.com.au/_next/data/20230404.03_v3.31.0/en"
    r = requests.get(url + "/product/" + str(id) + ".json")
    r = r.json()
    product = r['pageProps']['__N_REDIRECT']
    r = requests.get(url + product + ".json")
    r = r.json()
    id = r['pageProps']['product']['id']
    name = r['pageProps']['product']['name']
    brand = r['pageProps']['product']['brand']
    description = r['pageProps']['product']['description']
    current_price = r['pageProps']['product']['pricing']['now']

    if r.get('pageProps') and r['pageProps'].get('product') and r['pageProps']['product'].get('pricing') and r['pageProps']['product']['pricing'].get('promotionType'):
        on_sale = True
    else:
        on_sale = False

    return (id, name, brand, description, current_price, on_sale)