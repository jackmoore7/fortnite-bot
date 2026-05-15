import json
import os
import re
import time
import urllib.parse
from datetime import datetime as dt
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from imports.core_utils import cursor

BASE_URL = "https://www.coles.com.au"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/html, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

select_coles_version = "SELECT version FROM coles_version"

def update_build_number():
    build_version = cursor.execute(select_coles_version).fetchone()[0]
    url = "https://www.coles.com.au/_next/data/"
    r = requests.get(url, headers=HEADERS)
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
    r = requests.get(url + build_version + "/en/search/products.json?q=" + query, headers=HEADERS, verify=False)
    if r.status_code == 404:
        update_build_number()
        build_version = cursor.execute(select_coles_version).fetchone()[0]
        r = requests.get(url + build_version + "/en/search/products.json?q=" + query, headers=HEADERS, verify=False)
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
    r = requests.post(url, headers=HEADERS, json=payload, verify=False)
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
        online_special = item.get('pricing', {}).get('onlineSpecial', False)
        item_list.append([item_id, name, brand, description, current_price, on_sale, available, offer_description, multibuy_unit_price, image_url, promotion_type, online_special])
    data = {
        "invalid_ids": r['invalidProducts'],
        "items": item_list
    }
    return data

def get_latest_build_id():
    update_build_number()
    build_id = cursor.execute(select_coles_version).fetchone()[0]
    return build_id

def fetch_with_retry(url, params=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1} failed: {str(e)}")
            time.sleep(2 ** attempt)
    return None

def fetch_category_structure(build_id):
    url = f"{BASE_URL}/_next/data/{build_id}/browse.json"
    print(f"Fetching category structure from: {url}")
    
    response = fetch_with_retry(url)
    if not response or response.status_code != 200:
        print("Failed to fetch browse.json")
        return None
        
    try:
        return response.json()
    except Exception as e:
        print(f"Error parsing browse data: {str(e)}")
        return None

def extract_top_level_categories(browse_data):
    top_categories = []
    
    if not browse_data or "pageProps" not in browse_data:
        return top_categories
    
    try:
        catalog_group = browse_data["pageProps"]["allProductCategories"]
        
        for category in catalog_group.get("catalogGroupView", []):
            if "seoToken" in category and category.get("productCount", 0) > 0:
                top_categories.append({
                    "id": category["id"],
                    "name": category["name"],
                    "seo_token": category["seoToken"],
                    "product_count": category["productCount"]
                })
        return top_categories
    except KeyError as e:
        print(f"Key error extracting categories: {str(e)}")
        return top_categories

def fetch_category_products(category, build_id, page=1):
    url = f"{BASE_URL}/_next/data/{build_id}/browse/{category['seo_token']}.json"
    params = {"page": page}
    
    response = fetch_with_retry(url, params=params)
    if not response or response.status_code != 200:
        return [], 0
        
    try:
        data = response.json()
        search_results = data.get("pageProps", {}).get("searchResults", {})
        products = search_results.get("results", [])
        total_count = search_results.get("noOfResults", 0)
        return products, total_count
    except Exception as e:
        print(f"Error parsing category products: {str(e)}")
        return [], 0

def parse_product(product_data):
    if not product_data or not isinstance(product_data, dict):
        return None
        
    product = {
        "id": product_data.get("id", ""),
        "name": product_data.get("name", ""),
        "brand": product_data.get("brand", ""),
        "description": product_data.get("description", ""),
        "size": product_data.get("size", ""),
        "availability": product_data.get("availability", "Unknown"),
        "sku": product_data.get("sku", ""),
        "ad_id": product_data.get("adId", ""),
    }
    
    pricing = product_data.get("pricing", {})
    if not pricing or not isinstance(pricing, dict):
        product["pricing"] = {
            "now": 0,
            "was": 0,
            "save_amount": 0,
            "price_description": "",
            "save_percent": 0,
            "unit_price": 0,
        }
    else:
        product["pricing"] = {
            "now": pricing.get("now", 0),
            "was": pricing.get("was", 0),
            "save_amount": pricing.get("saveAmount", 0),
            "price_description": pricing.get("priceDescription", ""),
            "save_percent": pricing.get("savePercent", 0),
            "unit_price": pricing.get("unit", {}).get("price", 0) if pricing.get("unit") else 0,
        }
    
    if "urlFriendlyName" in product_data:
        product["url"] = urljoin(BASE_URL, product_data["urlFriendlyName"])
    elif "friendlyUrlNext" in product_data:
        product["url"] = urljoin(BASE_URL, product_data["friendlyUrlNext"])
    else:
        name_slug = re.sub(r'[^\w-]+', '-', product.get("name", "product").lower())[:50]
        product["url"] = f"{BASE_URL}/product/{name_slug}/p/{product['id']}"
    
    images = []
    for uri in product_data.get("imageUris", []):
        if "uri" in uri:
            images.append({
                "url": f"https://cdn.productimages.coles.com.au/productimages{uri['uri']}",
                "type": uri.get("type", "default"),
                "alt": uri.get("altText", "")
            })
    product["images"] = images
    
    return product

def process_category(category, build_id):
    print(f"Processing {category['name']} (ID: {category['id']})")
    all_products = []
    page = 1
    total_products_expected = category.get("product_count", 0)
    
    while True:
        time.sleep(0.5)
        
        try:
            products, total_products = fetch_category_products(category, build_id, page)
        except Exception as e:
            print(f"Error fetching page {page}: {str(e)}")
            products = []
        
        if not products:
            print(f"Page {page} returned no products, stopping")
            break
            
        parsed_products = []
        for item in products:
            if item.get("_type") == "PRODUCT":
                product = parse_product(item)
                if product:
                    product["category_id"] = category["id"]
                    product["category_name"] = category["name"]
                    product["category_seo_token"] = category["seo_token"]
                    parsed_products.append(product)
        
        count = len(parsed_products)
        all_products.extend(parsed_products)
        # print(f"Page {page}: {count} products")
        
        if count == 0:
            print("No products parsed, stopping")
            break
            
        if len(all_products) >= total_products_expected:
            break
            
        if len(all_products) >= total_products:
            break
            
        if page >= 150:
            print("Reached maximum page limit (150)")
            break
            
        if count < 36:
            print("Short page detected, likely end of products")
            break
            
        page += 1
    
    print(f"Completed: {len(all_products)} products (expected: {total_products_expected})")
    return all_products

def save_category_data(category, products, build_id):
    os.makedirs("coles_data", exist_ok=True)
    timestamp = dt.now().strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r'[^a-z0-9]+', '-', category["name"].lower())
    filename = f"coles_{slug}_{timestamp}.json"
    filepath = os.path.join("coles_data", filename)
    
    output = {
        "metadata": {
            "category_id": category["id"],
            "category_name": category["name"],
            "seo_token": category["seo_token"],
            "expected_products": category["product_count"],
            "scraped_products": len(products),
            "scraped_at": timestamp,
            "build_id": build_id
        },
        "products": products
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(products)} products to {filepath}")
    return filepath

def get_items_from_files(directory="coles_data"):
    item_list = []
    invalid_ids = []

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ Skipping invalid JSON file: {filename}")
                continue

        products = data.get("products", [])
        if not products:
            continue

        for item in products:
            try:
                item_id = item["id"]
                name = item.get("name", "")
                brand = item.get("brand", "")
                description = item.get("description", "")
                image_url = item["images"][0]["url"] if item.get("images") else ""

                pricing = item.get("pricing", {})
                current_price = pricing.get("now")
                promotion_type = pricing.get("price_description", "")
                on_sale = bool(pricing.get("was")) and current_price is not None

                available = item.get("availability")
                offer_description = pricing.get("price_description", "")
                multibuy_unit_price = pricing.get("unit_price", "")

                item_list.append([
                    item_id,
                    name,
                    brand,
                    description,
                    current_price,
                    on_sale,
                    available,
                    offer_description,
                    multibuy_unit_price,
                    image_url,
                    promotion_type
                ])

            except KeyError as e:
                print(f"⚠️ Missing key {e} in {filename}, skipping item.")
                invalid_ids.append(item.get("id"))

    data = {
        "invalid_ids": invalid_ids,
        "items": item_list
    }
    return data

def try_bad_boys():
    error_ids = cursor.execute("SELECT id FROM coles_error_ids").fetchall()
    error_ids = [x[0] for x in error_ids]
    url = "https://coles.com.au/api/products"
    for item in error_ids:
        payload = {"productIds":str(item)}
        r = requests.post(url, headers=HEADERS, json=payload)
        if r.status_code != 500:
            cursor.execute("INSERT INTO coles_active_ids (id) VALUES (?)", (item,))
            cursor.execute("DELETE FROM coles_error_ids WHERE id = ?", (item,))
            print(f"{item} is no longer throwing an error and was added to the active IDs database.")
