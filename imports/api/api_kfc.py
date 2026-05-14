import os
import uuid
from datetime import datetime as dt
from urllib.parse import urlparse

import aiohttp
from dotenv import load_dotenv

from imports.core_utils import cursor

json_application = "application/json"
user_agent = "okhttp/4.10.0"

load_dotenv()

async def refresh_token():
	now = dt.now().isoformat()
	print(f"[{now}] Attempting to refresh token")
	token_row = cursor.execute("SELECT client_id, refresh_token FROM kfc_tokens").fetchone()
	if not token_row:
		print(f"[{now}] KFC token refresh failed: kfc_tokens row not found")
		return None

	client_id, ref_token = token_row
	payload = {
		"client_id": client_id,
		"grant_type": "refresh_token",
		"refresh_token": ref_token
	}
	timeout = aiohttp.ClientTimeout(total=15)
	headers = {
		"Accept": json_application,
		"Content-Type": "application/x-www-form-urlencoded",
		"User-Agent": user_agent
	}
	try:
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.post(
				"https://login.kfc.com.au/auth/realms/kau/protocol/openid-connect/token",
				data=payload,
				headers=headers,
			) as response:
				text = await response.text()
				if response.status == 200:
					data = await response.json()
					access_token = data["access_token"]
					ref_token = data["refresh_token"]
					print(f"[{now}] Refresh succeeded: new access token received")
					cursor.execute("UPDATE kfc_tokens SET access_token = ?, refresh_token = ?", (access_token, ref_token))
					print(f"[{now}] New token saved to database")
					return access_token
				else:
					print(f"[{now}] Couldn't refresh token, status={response.status}, response={text}")
					return None
	except Exception as e:
		print(f"[{now}] KFC refresh_token failed: {type(e).__name__}: {e}")
		return None
	
def get_access_token():
	access_token = cursor.execute("SELECT access_token FROM kfc_tokens").fetchone()[0]
	return access_token

async def get_active_basket():
	now = dt.now().isoformat()
	x_correlation_request_id = str(uuid.uuid4())
	x_correlation_session_id = str(uuid.uuid4())
	access_token = get_access_token()
	user_id = os.getenv("KFC_USER_ID")
	email = os.getenv("KFC_USER_EMAIL")
	phone = os.getenv("KFC_USER_PHONE")
	url = f"https://orderserv-kfc-apac-olo-api.yum.com/dev/v1/customers/{user_id}/signed-in"

	print(f"[{now}] get_active_basket request: user_id={user_id}, access_token_present={bool(access_token)}")

	payload = {
		"firstName": "A",
		"lastName": "N",
		"emailId": email,
		"phoneNumber": phone,
		"attributes": {
			"birthDay": None,
			"birthYear": None,
			"birthMonth": None,
			"postalCode": None
		}
	}
	headers = {
		"accept": json_application,
		"x-tenant-id": "afd3813afa364270bfd33f0a8d77252d",
		"x-is-registered-user": "true",
		"x-user-id": user_id,
		"authorization": f"Bearer {access_token}",
		"x-correlation-request-id": x_correlation_request_id,
		"x-correlation-session-id": x_correlation_session_id,
		"app-source": "mobile",
		"content-type": json_application,
		"host": "orderserv-kfc-apac-olo-api.yum.com",
		"connection": "Keep-Alive",
		"accept-encoding": "gzip",
		"user-agent": user_agent
	}

	timeout = aiohttp.ClientTimeout(total=15)
	try:
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.post(url, json=payload, headers=headers) as response:
				text = await response.text()
				if response.status == 200:
					data = await response.json()
					basket_id = data["customer"]["basic"]["inProgressBasketId"]
					print(basket_id)
					return basket_id
				elif response.status == 401:
					print("Couldn't get active basket, unauthorized. Refreshing access token.")
					refreshed = await refresh_token()
					if refreshed:
						return await get_active_basket()
					return None
				else:
					print(f"Couldn't get active basket, non-200 response: {response.status} {text}")
					return None
	except Exception as e:
		print(f"{now} get_active_basket failed: {type(e).__name__}: {e}")
		return None

def is_valid_http_url(url):
	try:
		parsed = urlparse(url)
		return parsed.scheme in ("http", "https") and bool(parsed.netloc)
	except Exception:
		return False

async def get_promos(basket_id):
	access_token = get_access_token()
	url = f"https://orderserv-kfc-apac-olo-api.yum.com/dev/v1/baskets/{basket_id}/applicable-coupons"

	headers = {
		"accept": "application/json",
		"x-tenant-id": "afd3813afa364270bfd33f0a8d77252d",
		"authorization": f"Bearer {access_token}",
		"x-correlation-request-id": "0519f438-54fd-451a-b969-b58d957095b5",
		"x-correlation-session-id": "d0f2db81-f2f8-43cc-b030-627b6bac6bd6",
		"app-source": "mobile",
		"host": "orderserv-kfc-apac-olo-api.yum.com",
		"connection": "Keep-Alive",
		"accept-encoding": "gzip",
		"user-agent": user_agent
	}

	promo_list = []
	timeout = aiohttp.ClientTimeout(total=15)
	now = dt.now().isoformat()
	print(f"[{now}] get_promos request: basket_id={basket_id}")
	try:
		async with aiohttp.ClientSession(timeout=timeout) as session:
			async with session.get(url, headers=headers) as response:
				text = await response.text()
				if response.status == 200:
					data = await response.json()
					print(f"[{now}] get_promos received {len(data)} promo items")
					for item in data:
						start_date = f"<t:{int(item["startDateTime"])}:R>"
						end_date = f"<t:{int(item["endDateTime"])}:R>"
						global_redeems = item["usageCount"]
						promo_details = item["promotionDetails"]
						title = promo_details["title"][0]["value"]
						description = promo_details["description"][0]["value"]
						image_url = None
						for image_field in ("imageUrl", "image_url", "image", "thumbnail", "imageURL"):
							if image_field in promo_details and promo_details[image_field]:
								candidate = promo_details[image_field]
								if isinstance(candidate, str) and is_valid_http_url(candidate):
									image_url = candidate
									break
								if isinstance(candidate, dict):
									candidate_value = candidate.get("value")
									if candidate_value and is_valid_http_url(candidate_value):
										image_url = candidate_value
										break
						if not image_url and isinstance(promo_details.get("media"), list) and promo_details["media"]:
							candidate = promo_details["media"][0].get("value")
							if candidate and is_valid_http_url(candidate):
								image_url = candidate
						if not image_url:
							candidate = item.get("imageUrl") or item.get("image_url")
							if candidate and is_valid_http_url(candidate):
								image_url = candidate
						if not image_url and isinstance(item.get("itemDetails"), list):
							for detail in item["itemDetails"]:
								if isinstance(detail, dict):
									if isinstance(detail.get("imageName"), list) and detail["imageName"]:
										candidate = detail["imageName"][0].get("value")
										if candidate and is_valid_http_url(candidate):
											image_url = candidate
											break
									content_image = detail.get("content", {}).get("image", {}).get("mainImage")
									if content_image and is_valid_http_url(content_image):
										image_url = content_image
										break
						deal_id = str(item.get("id") or promo_details.get("promotionId") or f"{title}-{start_date}-{end_date}")
						promo_list.append({
							"deal_id": deal_id,
							"start_date": start_date,
							"end_date": end_date,
							"global_redeems": global_redeems,
							"title": title,
							"description": description,
							"image_url": image_url
						})
					return promo_list
				elif response.status == 401:
					print("Couldn't get promos, unauthorized. Refreshing access token.")
					refreshed = await refresh_token()
					if refreshed:
						return await get_promos(basket_id)
					return []
				else:
					print(f"Couldn't get promos, non-200 response: {response.status} {text}")
					return []
	except Exception as e:
		print(f"get_promos failed: {type(e).__name__}: {e}")
		refreshed = await refresh_token()
		if refreshed:
			return await get_promos(basket_id)
		return []


async def get_kfc_deals():
	basket_id = await get_active_basket()
	if not basket_id:
		return []
	promos = await get_promos(basket_id)
	return promos or []