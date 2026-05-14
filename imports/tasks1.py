import os
import shutil
import uuid
from datetime import datetime as dt
from datetime import time, timedelta
from time import mktime

import discord
import feedparser
import matplotlib.pyplot as plt

# import imghdr
import pytz
import requests
from bs4 import BeautifulSoup
from discord.ext import tasks
from icalendar import Calendar
from matplotlib.dates import DateFormatter
from PIL import Image

import imports.api.api_coles as api_coles
import imports.api.api_epic as api_epic
import imports.api.api_kfc as api_kfc
import imports.api.api_lego as api_lego
import imports.api.api_seveneleven as api_seveneleven
import imports.api.api_third_party as api_third_party
import imports.helpers as helpers
import imports.uv as uv
from imports.api import api_openai
from imports.core_utils import cursor, discord_client, mongo_client, tasks_list

mongo_db = mongo_client["coles"]
coles_updates_collection = mongo_db["coles_updates"]
timezone = "Australia/Sydney"
uv_plot_filename = "uv_index_plot.png"

start_time = time(20, 1, 0)
end_time = time(7, 0, 0)
time_list = [time(hour, minute) for hour in range(start_time.hour, 24) for minute in range(0, 60, 1)] + [time(hour, minute) for hour in range(end_time.hour + 1) for minute in range(0, 60, 1)]
coles_time = [time(19, 1)]

async def tasks_on_ready():
	await discord_client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="me booty arrrr"))
	if not fortnite_update_bg.is_running():
		fortnite_update_bg.start()
	# if not tv_show_update_bg.is_running():
	# 	tv_show_update_bg.start()
	if not fortnite_status_bg.is_running():
		fortnite_status_bg.start()
	if not coles_specials_bg.is_running():
		coles_specials_bg.start()
	if not arpansa.is_running():
		arpansa.start()
	if not epic_free_games.is_running():
		epic_free_games.start()
	if not ozb_bangers.is_running():
		ozb_bangers.start()
	# if not gog_free_games.is_running():
	# 	gog_free_games.start()
	# if not lego_bg.is_running():
	# 	lego_bg.start()
	if not fuel_check.is_running():
		fuel_check.start()
	# if not fortnite_shop_update_v3.is_running():
	# 	fortnite_shop_update_v3.start()
	if not coles_updates.is_running():
		coles_updates.start()
	if not check_scheduled_maintenance.is_running():
		check_scheduled_maintenance.start()
	if not tv_updates.is_running():
		tv_updates.start()
	if not stat_updates.is_running():
		stat_updates.start()
	if not kfc_deals_bg.is_running():
		kfc_deals_bg.start()
	tasks_list["update"] = fortnite_update_bg
	tasks_list["tv"] = tv_show_update_bg
	tasks_list["status"] = fortnite_status_bg
	tasks_list["coles"] = coles_specials_bg
	tasks_list["arpansa"] = arpansa
	tasks_list["free_games"] = epic_free_games
	tasks_list["ozb_bangers"] = ozb_bangers
	tasks_list["lego"] = lego_bg
	tasks_list["shop"] = fortnite_shop_update_v3
	tasks_list["tv_updates"] = tv_updates
	tasks_list["stat_updates"] = stat_updates
	tasks_list["kfc"] = kfc_deals_bg

	print(f"{discord_client.user} is online! My PID is {os.getpid()}.")

@tasks.loop(time=time_list, reconnect=True)
async def arpansa():
	try:
		ch = discord_client.get_channel(int(os.getenv("UV_CHANNEL")))
		role = os.getenv("SUNSCREEN_ROLE")
		current_date = dt.now(helpers.timezone).strftime("%Y-%m-%d")
		current_time = (dt.now(helpers.timezone) - timedelta(minutes=1)).strftime("%H:%M")
		db_date = cursor.execute("SELECT start FROM uv_times").fetchone()[0]
		data = uv.get_arpansa_data()

		current_uv = float(data["CurrentUVIndex"])
		max_uv_today_recorded = float(data["MaximumUVLevel"])
		max_uv_today_recorded_time = data["MaximumUVLevelDateTime"][-5:]
		r = data["GraphData"]
		forecast_graph = [entry["Forecast"] for entry in r]
		measured_graph = [entry["Measured"] for entry in r]
		dates_graph = [dt.strptime(entry["Date"], "%Y-%m-%d %H:%M") for entry in r]

		plt.figure(figsize=(12, 6))
		plt.fill_between(dates_graph, 0, 3, color="green", alpha=0.3, label="Low")
		plt.fill_between(dates_graph, 3, 6, color="yellow", alpha=0.3, label="Moderate")
		plt.fill_between(dates_graph, 6, 8, color="orange", alpha=0.3, label="High")
		plt.fill_between(dates_graph, 8, 11, color="red", alpha=0.3, label="Very High")
		plt.fill_between(dates_graph, 11, 16, color="purple", alpha=0.3, label="Extreme")
		plt.plot(dates_graph, forecast_graph, label="Forecast", linestyle="--", color="blue")
		plt.plot(dates_graph, measured_graph, label="Measured", color="orange")
		plt.xlim(dates_graph[0], dates_graph[-1])
		plt.ylim(0, 16)
		plt.xticks(rotation=0)
		plt.gca().xaxis.set_major_formatter(DateFormatter("%H:%M"))
		plt.yticks(range(0, 17))
		plt.grid(True, linestyle="--", alpha=0.5)
		plt.legend()
		plt.tight_layout()
		plt.savefig(uv_plot_filename)
		plt.close()

		if db_date != current_date:
			print("It's a new day!")

			first_forecast_gte_3_item = next(
				(item for item in r if item["Forecast"] is not None and item["Forecast"] >= 3),
				None
			)
			max_uv_today_forecast = max((item["Forecast"] for item in r if item["Forecast"] is not None), default=0)
			max_uv_today_forecast_time = next(
				(item["Date"][-5:] for item in r if item["Forecast"] == max_uv_today_forecast),
				"N/A"
			)

			embed = discord.Embed(color=0xa3c80a)

			if first_forecast_gte_3_item:
				first_forecast_index = r.index(first_forecast_gte_3_item)
				first_forecast_lt_3_item = next(
					(item for item in r[first_forecast_index + 1:] if item["Forecast"] is not None and item["Forecast"] < 3),
					None
				)
				forecast_time_range = f"{first_forecast_gte_3_item["Date"][-5:]} - {first_forecast_lt_3_item["Date"][-5:]}" if first_forecast_lt_3_item else f"{first_forecast_gte_3_item["Date"][-5:]} onwards"
				embed.title = "Sun protection required today"
			else:
				forecast_time_range = "No high UV forecasted"
				embed.title = "No sun protection required today"

			embed.add_field(name="Time (Forecast)", value=forecast_time_range, inline=False)

			first_recorded_gte_3_item = next(
				(item for item in r if item["Measured"] is not None and item["Measured"] >= 3),
				None
			)
			last_recorded_gte_3_item = next(
				(item for item in reversed(r) if item["Measured"] is not None and item["Measured"] >= 3),
				None
			)
			recorded_time_range = f"{first_recorded_gte_3_item["Date"][-5:]} - {last_recorded_gte_3_item["Date"][-5:]}" if first_recorded_gte_3_item else "No high UV recorded"
			embed.add_field(name="Time (Recorded)", value=recorded_time_range, inline=False)

			embed.add_field(name="Maximum UV (Forecast)", value=f"{uv.calculate_emoji(max_uv_today_forecast)} {max_uv_today_forecast} at {max_uv_today_forecast_time}", inline=False)
			embed.add_field(name="Maximum UV (Recorded)", value=f"{uv.calculate_emoji(max_uv_today_recorded)} {max_uv_today_recorded} at {max_uv_today_recorded_time}", inline=False)
			embed.add_field(name="Current UV", value=f"{uv.calculate_emoji(current_uv)} {current_uv} at {current_time}", inline=False)

			msg = await ch.send(embed=embed)
			cursor.execute("UPDATE uv_times SET end = ?", (msg.id,))
			cursor.execute("UPDATE uv_times SET start = ?", (current_date,))
			cursor.execute("UPDATE uv_times SET safe = ?", (0 if first_forecast_gte_3_item else 1,))

		msg = await ch.fetch_message(int(cursor.execute("SELECT end FROM uv_times").fetchone()[0]))
		emb = msg.embeds[0]

		first_recorded_gte_3_item = next(
			(item for item in r if item["Measured"] is not None and item["Measured"] >= 3),
			None
		)
		last_recorded_gte_3_item = next(
			(item for item in reversed(r) if item["Measured"] is not None and item["Measured"] >= 3),
			None
		)
		recorded_time_range = f"{first_recorded_gte_3_item["Date"][-5:]} - {last_recorded_gte_3_item["Date"][-5:]}" if first_recorded_gte_3_item else "No high UV recorded"
		emb.set_field_at(1, name="Time (Recorded)", value=recorded_time_range, inline=False)

		emb.set_field_at(-2, name="Maximum UV (Recorded)", value=f"{uv.calculate_emoji(max_uv_today_recorded)} {max_uv_today_recorded} at {max_uv_today_recorded_time}", inline=False)
		emb.set_field_at(-1, name="Current UV", value=f"{uv.calculate_emoji(current_uv)} {current_uv} at {current_time}")
		emb.color = discord.Color(uv.calculate_hex(current_uv))

		file = discord.File(uv_plot_filename, filename=uv_plot_filename)
		emb.set_image(url=f"attachment://{uv_plot_filename}")
		await msg.edit(embed=emb, file=file)
		await ch.edit(name=f"{uv.calculate_emoji(current_uv)} {round(current_uv)}")

		safe = bool(cursor.execute("SELECT safe FROM uv_times").fetchone()[0])
		if safe and current_uv >= 3:
			await ch.send(f"<@&{role}> Earlier forecast was incorrect - UV index is now above safe levels. slip slop slap bitch")
			cursor.execute("UPDATE uv_times SET safe = 0")

	except Exception as e:
		print(f"ARPANSA task encountered an exception: {e}.\nWill reconnect automatically.")

@tasks.loop(minutes=5, reconnect=True)
async def fortnite_update_bg():
	try:
		channel = discord_client.get_channel(int(os.getenv("UPD8_CHANNEL")))
		response = api_epic.get_fortnite_update_manifest()
		current_version = cursor.execute("SELECT version FROM aes").fetchone()[0]
		if current_version != response:
			cursor.execute("UPDATE aes SET version = ?", (response,))
			embed = discord.Embed(title="A new Fortnite update was just deployed")
			embed.add_field(name="Build", value=response, inline=False)
			await channel.send("<@&" + os.getenv("UPD8_ROLE") + ">", embed=embed)
	except Exception as e:
		print("Something went wrong getting the Fortnite manifest: " + str(repr(e)))

@tasks.loop(minutes=180, reconnect=True)
async def check_scheduled_maintenance():
	try:
		channel = discord_client.get_channel(int(os.getenv("UPD8_CHANNEL")))
		maintenances = api_epic.get_fortnite_maintenance()
		if not maintenances:
			return
		for maintenance in maintenances:
			maintenance_id = maintenance["id"]
			if cursor.execute("SELECT 1 FROM scheduled_maintenance WHERE id = ?", (maintenance_id,)).fetchone():
				continue
			utc_start = dt.strptime(maintenance["scheduled_for"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc)
			utc_end = dt.strptime(maintenance["scheduled_until"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc)
			sydney_start = int(utc_start.astimezone(pytz.timezone(timezone)).timestamp())
			sydney_end = int(utc_end.astimezone(pytz.timezone(timezone)).timestamp())
			start_time = f"<t:{sydney_start}:R>"
			end_time = f"<t:{sydney_end}:R>"
			embed = discord.Embed(title="Scheduled maintenance", description=maintenance["name"])
			embed.add_field(name="Starts", value=start_time, inline=False)
			embed.add_field(name="Ends", value=end_time, inline=False)
			await channel.send("<@&" + os.getenv("UPD8_ROLE") + ">", embed=embed)
			cursor.execute("INSERT INTO scheduled_maintenance (id) VALUES (?)", (maintenance_id,))
	except Exception as e:
		print(f"Error checking maintenance: {repr(e)}")

@tasks.loop(minutes=5, reconnect=True)
async def fortnite_status_bg():
	try:
		channel = discord_client.get_channel(int(os.getenv("UPD8_CHANNEL")))
		response = api_epic.get_fortnite_status()
		current_status = cursor.execute("SELECT * FROM server").fetchall()[0][0]
		if current_status != response:
			cursor.execute("UPDATE server SET status = ?", (response,))
			embed = discord.Embed(title = "Fortnite server status update")
			embed.add_field(name="Status", value=response)
			await channel.send("<@&" + os.getenv("UPD8_ROLE") + ">", embed=embed)
	except Exception as e:
		print(f"Something went wrong getting the Fortnite status: {str(repr(e))}")

@tasks.loop(minutes=5)
async def fortnite_shop_update_v3():

	def process_image(url, name):
		new_uuid = str(uuid.uuid4())
		img = requests.get(url)
		img_type = imghdr.what(None, h=img.content)
		if img_type:
			max_retries = 5
			for attempt in range(max_retries):
				try:
					with open(f"temp_images/{new_uuid}.{img_type}", "wb") as f:
						f.write(img.content)
					image = Image.open(f"temp_images/{new_uuid}.{img_type}")
					image.verify()
					print(f"{new_uuid} was successfully downloaded and verified")
					return f"{new_uuid}.{img_type}"
				except Exception as e:
					print(f"Broken image detected: {e}")
					os.remove(f"temp_images/{new_uuid}.{img_type}")
					if attempt < max_retries - 1:
						print(f"Retrying ({attempt + 1}/{max_retries})...")
					else:
						print(f"Max retries reached, failed to download {new_uuid}")
						no_images.append(name)
						break
		else:
			no_images.append(name)

	channel = discord_client.get_channel(int(os.getenv("SHOP2_CHANNEL")))
	r = api_third_party.fortnite_shop_v3()
	date = cursor.execute("SELECT date FROM shop_v3").fetchone()[0]
	new_date = r["data"]["date"]
	if new_date != date:
		vbucks_emoji = discord_client.get_emoji(int(os.getenv("VBUCKS_EMOJI")))
		ping_list = cursor.execute("SELECT item, id FROM shop_ping").fetchall()
		no_images = []
		daily = []
		for item in r["data"]["daily"]:
			if isinstance(item["history"], bool) or (item["history"].get("dates") and len(item["history"]["dates"]) < 2):
				if "featured" in item["images"] and item["images"]["featured"]:
					daily.append((item["images"]["featured"], item["name"], item["history"], item["price"]))
				elif "icon" in item["images"] and item["images"]["icon"]:
					daily.append((item["images"]["icon"], item["name"], item["history"], item["price"]))
				else:
					no_images.append((item["name"], item["history"], item["price"]))
			else:
				if "featured" in item["images"] and item["images"]["featured"]:
					daily.append((item["images"]["featured"], item["name"], sorted(item["history"]["dates"])[-2], item["price"]))
				elif "icon" in item["images"] and item["images"]["icon"]:
					daily.append((item["images"]["icon"], item["name"], sorted(item["history"]["dates"])[-2], item["price"]))
				else:
					no_images.append((item["name"], sorted(item["history"]["dates"])[-2], item["price"]))
		featured = []
		for item in r["data"]["featured"]:
			if isinstance(item["history"], bool) or (item["history"].get("dates") and len(item["history"]["dates"]) < 2):
				if "featured" in item["images"] and item["images"]["featured"]:
					featured.append((item["images"]["featured"], item["name"], item["history"], item["price"]))
				elif "icon" in item["images"] and item["images"]["icon"]:
					featured.append((item["images"]["icon"], item["name"], item["history"], item["price"]))
				else:
					no_images.append((item["name"], item["history"], item["price"]))
			else:
				if "featured" in item["images"] and item["images"]["featured"]:
					featured.append((item["images"]["featured"], item["name"], sorted(item["history"]["dates"])[-2], item["price"]))
				elif "icon" in item["images"] and item["images"]["icon"]:
					featured.append((item["images"]["icon"], item["name"], sorted(item["history"]["dates"])[-2], item["price"]))
				else:
					no_images.append((item["name"], sorted(item["history"]["dates"])[-2], item["price"]))
		yesterday = cursor.execute("SELECT * FROM shop_v3_content").fetchall()
		diff = [item for item in featured if item[1] not in (item[1] for item in yesterday)]
		if len(diff) < 1:
			diff2 = [item for item in yesterday if item[1] not in (item[1] for item in featured)]
			if len(diff2) > 0:
				await channel.send("The following items were just deleted from the shop:")
				for item in diff2:
					await channel.send(f"{item[1]}")
			cursor.execute("UPDATE shop_v3 SET date = ?", (new_date,))
			return
		print(f"daily: {len(daily)}")
		print(f"featured: {len(featured)}")
		print(f"diff: {len(diff)}")
		await channel.send("# Fortnite shop update")
		await channel.send(f"{(len(daily) + len(diff))} items were just added to the shop.")
		for item in daily:
			img = process_image(item[0], item[1])
			matching_items = [i for i, u in ping_list if i.lower() in item[1].lower()]
			for cosmetic in matching_items:
				users = [u for i, u in ping_list if i == cosmetic]
				for user in users:
					await channel.send(f"<@{user}>, {item[1]} is in the shop\nTriggered by your keyword: {cosmetic}")
			await channel.send(f"{item[1]} - Last seen {helpers.timestampify_z(item[2])}", file=discord.File(f"temp_images/{img}"))
			os.remove(f"temp_images/{img}")
		for item in diff:
			img = process_image(item[0], item[1])
			matching_items = [i for i, u in ping_list if i.lower() in item[1].lower()]
			for cosmetic in matching_items:
				users = [u for i, u in ping_list if i == cosmetic]
				for user in users:
					await channel.send(f"<@{user}>, {item[1]} is in the shop\nTriggered by your keyword: {cosmetic}")
			if isinstance(item[2], (bool, dict)):
				await channel.send(f"## {item[1]} - {item[3]} {vbucks_emoji}\nFirst appearance in the shop!", file=discord.File(f"temp_images/{img}"))
			else:
				await channel.send(f"## {item[1]} - {item[3]} {vbucks_emoji}\nLast seen: {helpers.timestampify_z(item[2])}", file=discord.File(f"temp_images/{img}"))
			os.remove(f"temp_images/{img}")
		if no_images:
			await channel.send("The following items did not have associated images or failed to download after multiple attempts:")
			for item in no_images:
				await channel.send(item)
		cursor.execute("DELETE FROM shop_v3_content")
		cursor.executemany("INSERT INTO shop_v3_content VALUES (?, ?)", [(item[0], item[1]) for item in featured])
		cursor.execute("UPDATE shop_v3 SET date = ?", (date,))

@tasks.loop(minutes=180, reconnect=True)
async def coles_specials_bg():
	channel = discord_client.get_channel(int(os.getenv("COLES_SPECIALS_CHANNEL")))
	product_url = "https://www.coles.com.au/product/"
	
	# Use the global cursor
	items_old = cursor.execute("SELECT * FROM coles_specials").fetchall()
	item_ids_list = [item[0] for item in items_old]
	
	results = api_coles.get_items(item_ids_list)
	items_new = results["items"]
	
	# Map old items by ID for comparison
	old_map = {item[0]: item for item in items_old}

	for item_new in items_new:
		item_id = item_new[0] 
		old_item = old_map.get(item_id)
		
		if not old_item: 
			continue

		# Compare Price (index 4), Sale (5), Available (6)
		p_old = old_item[4]
		p_new = item_new[4]
		price_changed = p_old != p_new
		
		# Check for any significant changes
		if price_changed or old_item[5] != item_new[5] or old_item[6] != item_new[6]:
			current_date = dt.now(pytz.timezone(timezone)).strftime("%Y-%m-%d %H:%M:%S")
			
			# 1. Update basic info in Database
			cursor.execute("UPDATE coles_specials SET current_price=?, on_sale=?, available=? WHERE id=?", 
						  (p_new, item_new[5], item_new[6], item_id))

			# 2. AI Logic
			ai_data = api_openai.coles_recommendation(item_id, p_new, current_date)
			ai_status, ai_rec, ai_logic = ai_data.current_status, ai_data.recommendation, ai_data.logic
			
			cursor.execute("UPDATE coles_specials SET ai_status=?, ai_recommendation=?, ai_logic=? WHERE id=?", 
						  (ai_status, ai_rec, ai_logic, item_id))

			# 3. Build the Embed
			embed = discord.Embed(
				title=f"{item_new[2]} {item_new[1]}",
				url=product_url + str(item_id), 
				color=0xe01a22
			)
			
			if len(item_new) > 9 and item_new[9]:
				embed.set_thumbnail(url=item_new[9])

			promo_type = item_new[10] if len(item_new) > 10 else ""
			online_special = item_new[11] if len(item_new) > 11 else False
			field_names = ["Price", "Promotion", "Available"]
			for name, old_value, new_value in zip(field_names, old_item[4:7], item_new[4:7]):
				if name == "Price":
					if new_value is None:
						field_value = f"~~${old_value}~~\nPrice not specified"
					else:
						field_value = f"~~${old_value}~~\n${float(new_value)} ({helpers.percentage_change(old_value, new_value)})" if old_value != new_value else f"${new_value}"
				elif name == "Promotion":
					display_new = "Yes" if new_value else "No"
					if promo_type:
						display_new += f" ({promo_type})"
						if online_special:
							display_new += " (ONLINE ONLY)"
					display_old = "Yes" if old_value else "No"
					field_value = f"~~{display_old}~~\n{display_new}" if old_value != new_value else display_new
				else:
					display_new = "Yes" if new_value else "No"
					display_old = "Yes" if old_value else "No"
					field_value = f"~~{display_old}~~\n{display_new}" if old_value != new_value else display_new
					if display_new == "No":
						embed.color = 0x000000
				embed.add_field(name=name, value=field_value, inline=False)
			
			if len(item_new) > 7 and item_new[7]:
				promo_val = f"{item_new[7]}"
				if len(item_new) > 8 and item_new[8]:
					promo_val += f" - reduces price per unit to ${item_new[8]}"
				embed.add_field(name="Promotion details", value=promo_val, inline=False)
			
			embed.add_field(name="Recommendation", value=f"**{ai_rec}** ({ai_status})\n{ai_logic}", inline=False)
			
			await channel.send(embed=embed)

@tasks.loop(minutes=30)
async def lego_bg():
	# try:
	channel = discord_client.get_channel(int(os.getenv("LEGO_CHANNEL")))
	product_url = "https://www.lego.com/en-au/product/"
	items_old = cursor.execute("SELECT * FROM lego").fetchall()
	items_new = []
	for item in items_old:
		result = api_lego.get_lego_item_by_id(item[0])
		if result:
			result = result["data"]["product"]
			product_code = int(result["productCode"])
			name = result["name"]
			image_url = result["baseImgUrl"]
			slug = result["slug"]
			availability = result["variant"]["attributes"]["availabilityText"]
			on_sale = result["variant"]["attributes"]["onSale"]
			price = result["variant"]["price"]["formattedAmount"]
			items_new.append((product_code, name, image_url, slug, availability, on_sale, price))

		if items_old != items_new:
			for new_item in items_new:
				cursor.execute("UPDATE lego SET name = ?, image_url = ?, slug = ?, availability = ?, on_sale = ?, price = ? WHERE id = ?", (new_item[1], new_item[2], new_item[3], new_item[4], new_item[5], new_item[6], new_item[0]))

		for item1, item2 in zip(items_old, items_new):
			differences_exist = any(old_value != new_value for old_value, new_value in zip(item1[3:], item2[3:]))

			if differences_exist:
				embed = discord.Embed(title=item2[1], url=product_url + item2[3])
				embed.set_thumbnail(url=item2[2])

				field_names = ["Availability", "On sale", "Price"]

				for name, old_value, new_value in zip(field_names, item1[4:], item2[4:]):
					field_value = f"~~{old_value}~~\n{new_value}" if old_value != new_value else new_value
					embed.add_field(name=name, value=field_value, inline=False)

				await channel.send(embed=embed)

	# except Exception as e:
	# 	await channel.send(f"Exception: {e}")

@tasks.loop(minutes=60)
async def epic_free_games():
	
	ch = discord_client.get_channel(int(os.getenv("BANGERS_CHANNEL")))

	def timestampify_and_convert_to_aest(string):
		utc_timezone = pytz.timezone("UTC")
		our_timezone = helpers.timezone
		date_time_obj = dt.strptime(string, helpers.time_format)
		date_time_obj = utc_timezone.localize(date_time_obj)
		our_time = date_time_obj.astimezone(our_timezone)
		struct_time = our_time.timetuple()
		timestamp = f"<t:{int(mktime(struct_time))}:R>"
		return timestamp

	def test_time(string):
		our_timezone = helpers.timezone
		end_dt = dt.strptime(string, helpers.time_format)
		end_dt = our_timezone.localize(end_dt)
		current_dt = dt.now(our_timezone)
		if current_dt > end_dt:
			return True
		else:
			return False
		
	def convert_to_aest(string):
		utc_timezone = pytz.timezone("UTC")
		our_timezone = helpers.timezone
		date_time_obj = dt.strptime(string, helpers.time_format)
		date_time_obj = utc_timezone.localize(date_time_obj)
		our_time = date_time_obj.astimezone(our_timezone)
		new_string = our_time.strftime(helpers.time_format)
		return new_string

	games_list = api_epic.get_free_games()
	posted = cursor.execute("SELECT * FROM free_games").fetchall()

	diff = [game for game in games_list if game[0] not in [posted_game[0] for posted_game in posted]]

	if len(diff) > 0:
		for game in diff:
			embed = discord.Embed()
			embed.title = "New free game on the Epic Games store"
			embed.set_image(url=game[2])
			embed.add_field(name="Title", value=game[0], inline=False)
			embed.add_field(name="Description", value=game[1], inline=False)
			embed.add_field(name="Starts", value=timestampify_and_convert_to_aest(game[3]))
			embed.add_field(name="Ends", value=timestampify_and_convert_to_aest(game[4]))
			await ch.send(f"<@&{os.getenv("FREE_GAMES_ROLE")}>", embed=embed)
			cursor.execute("INSERT INTO free_games VALUES (?, ?, ?, ?)", (game[0], game[1], game[2], convert_to_aest(game[4])))
	
	for game in posted:
		if test_time(game[3]):
			cursor.execute("DELETE FROM free_games WHERE title = ?", (game[0],))
			print(f"{game[0]} was deleted from the free_games database as the promotional period has ended.")

@tasks.loop(minutes=60)
async def gog_free_games():
	ch = discord_client.get_channel(int(os.getenv("FREE_GAMES_CHANNEL")))
	posted = cursor.execute("SELECT * FROM gog_free_games").fetchall()
	r = requests.get("https://www.gog.com/")
	soup = BeautifulSoup(r.content, "html.parser")
	giveaway = soup.find("a", {"id": "giveaway"})
	if giveaway:
		href = giveaway.get("ng-href")
		url = f"https://gog.com{href}"
		if url not in [x[0] for x in posted]:
			timestamp = giveaway.find_next("div", {"class": "giveaway-banner--with-consent__content"}).find("div", {"class": "giveaway-banner__footer"}).find("gog-countdown-timer")
			if timestamp:
				timestamp = f"<t:{int(timestamp["end-date"])//1000}:R>"
			else:
				timestamp = "Unknown"
			embed = discord.Embed()
			embed.title = "New free game on GOG"
			embed.description = url
			embed.add_field(name="Ends", value=timestamp)
			await ch.send(f"<@&{os.getenv("FREE_GAMES_ROLE")}>", embed=embed)
			cursor.execute("INSERT INTO gog_free_games VALUES (?)", (url,))
	else:
		cursor.execute("DELETE FROM gog_free_games")

@tasks.loop(minutes=30, reconnect=True)
async def tv_show_update_bg():
	try:
		user = discord_client.get_user(int(os.getenv("ME")))
		url = os.getenv("SHOWRSS")
		feed = feedparser.parse(url)
		last_guid = cursor.execute("select * from rss").fetchall()[0][0]
		if len(feed["entries"]) > 0:
			latest_guid = feed["entries"][0]["guid"]
		else:
			return
		if latest_guid != last_guid:
			rssembed = discord.Embed(title = "A new episode just released!")
			rssembed.add_field(name="Name", value=feed["entries"][0]["tv_raw_title"], inline=False)
			rssembed.add_field(name="Released", value=feed["entries"][0]["published"], inline=False)
			cursor.execute("UPDATE rss SET guid = ?", (latest_guid,))
			await user.send(embed = rssembed)
	except Exception as e:
		print(f"Something went wrong getting the TV show RSS: {str(repr(e))}")

@tasks.loop(minutes=10, reconnect=True)
async def ozb_bangers():
	try:
		feed = feedparser.parse("https://www.ozbargain.com.au/deals/feed")
		posted = cursor.execute("SELECT * FROM ozbargain").fetchall()
		for post in feed["entries"]:
			upvotes = int(post["ozb_meta"]["votes-pos"])
			downvotes = int(post["ozb_meta"]["votes-neg"])
			clicks = int(post["ozb_meta"]["click-count"])
			try:
				prefix = f"[{post["ozb_title-msg"]["type"].upper()}]"
			except Exception:
				prefix = ""
			if upvotes >= 200 and (post["link"] not in [x[0] for x in posted]) and (prefix != "[EXPIRED]"):
				try:
					expiry = helpers.timestampify(post["ozb_meta"]["expiry"])
				except Exception:
					expiry = "Unknown"
				title = post["title"]
				link = post["link"]
				upvote_emoji = discord_client.get_emoji(int(os.getenv("UPVOTE_EMOJI")))
				downvote_emoji = discord_client.get_emoji(int(os.getenv("DOWNVOTE_EMOJI")))
				ch = discord_client.get_channel(int(os.getenv("BANGERS_CHANNEL")))
				embed = discord.Embed()
				embed.title = f"{prefix} {title}"
				embed.description = f"{upvote_emoji} >={upvotes}\n{downvote_emoji} {downvotes}\nClicks: {clicks}"
				try:
					if post["ozb_meta"]["image"]:
						embed.set_image(url=post["ozb_meta"]["image"])
				except:
					print("No image associated with this banger.")
				embed.add_field(name="Link", value=link, inline=False)
				embed.add_field(name="Expires", value=expiry, inline=False)
				await ch.send(embed=embed)
				cursor.execute("INSERT INTO ozbargain VALUES (?)", (link,))
	except Exception as e:
		print(f"ozb_bangers encountered an exception: {e}")

@tasks.loop(minutes=5, reconnect=True)
async def fuel_check():
	channel = discord_client.get_channel(int(os.getenv("FUEL_CHANNEL")))
	try:
		response = api_seveneleven.check_lowest_fuel_price_p03()
		# last_updated = response[1]
		response = response[0]
		db_price = cursor.execute("SELECT * FROM fuel").fetchone()[0]
		if db_price != str(response["price"]):
			cursor.execute("UPDATE fuel SET price = ?", (str(response["price"]),))
			await channel.send(f"The cheapest fuel is {response["type"]} at {response["suburb"]} for {response["price"]}.")
	except Exception as e:
		print(f"fuel loop encountered an exception: {e}")

@tasks.loop(time=coles_time, reconnect=True)
async def tv_updates():
	try:
		today = dt.now().weekday()
		if today != 0: # 0 = monday
			return
		ch = discord_client.get_channel(int(os.getenv("PLEX_CHANNEL")))
		ics_url = str(os.getenv("ICS_URL"))

		now = dt.now(helpers.timezone)
		monday = now - timedelta(days=now.weekday())
		sunday = monday + timedelta(days=6)

		response = requests.get(ics_url)
		cal = Calendar.from_ical(response.content)

		events = []
		for component in cal.walk():
			if component.name == "VEVENT":
				start = component.get("dtstart").dt
				end = component.get("dtend").dt
				summary = str(component.get("summary"))
				description = str(component.get("description", ""))

				start = start.astimezone(helpers.timezone)
				end = end.astimezone(helpers.timezone)

				if start.date() >= monday.date() and start.date() <= sunday.date():
					events.append((start, end, summary, description))

		if events:
			embed = discord.Embed(title=f"TV Airing This Week ({monday.strftime("%b %d")} - {sunday.strftime("%b %d")})",
								  color=0x00ff00)
			for event in sorted(events, key=lambda x: x[0]):
				start_str = event[0].strftime("%a %b %d %I:%M %p")
				end_str = event[1].strftime("%I:%M %p")
				embed.add_field(
					name=f"{event[2]}",
					value=f"{start_str} - {end_str}\n{event[3]}",
					inline=False
				)
			await ch.send(embed=embed)
	except Exception as e:
		print(f"tv_updates task failed: {e}")

@tasks.loop(minutes=6)
async def stat_updates():
	token = os.getenv("HOME_ASSISTANT_LONG_LIVED_ACCESS_TOKEN")

	headers = {
		"Authorization": f"Bearer {token}",
		"Content-Type": "application/json",
	}

	channel = discord_client.get_channel(os.getenv("STAT_VC_1"))
	channel2 = discord_client.get_channel(os.getenv("STAT_VC_2"))

	import aiohttp
	try:
		async with aiohttp.ClientSession() as session:

			url_temp = "http://nas.jack.vc:8123/api/states/sensor.universal_remote_temperature"
			async with session.get(url_temp, headers=headers) as resp_temp:
				if resp_temp.status != 200:
					print("Home Assistant request for temperature failed:", resp_temp.status)
					return
				data_temp = await resp_temp.json()

			sensor_entity =	os.getenv("ABB_SENSOR_ENTITY")
			url_data_used = f"http://nas.jack.vc:8123/api/states/{sensor_entity}"
			async with session.get(url_data_used, headers=headers) as resp_data:
				if resp_data.status != 200:
					print(f"Home Assistant request for {sensor_entity} failed:", resp_data.status)
					data_data = None
				else:
					data_data = await resp_data.json()

	except Exception as e:
		print("Exception while querying Home Assistant:", e)
		return

	temperature = data_temp.get("state") if data_temp else None
	if channel and temperature is not None:
		try:
			await channel.edit(name=str(temperature) + "°C")
		except Exception as e:
			print("Failed to edit temperature channel:", e)

	if channel2:
		try:
			if data_data and "state" in data_data:
				await channel2.edit(name=str(data_data["state"]) + " TB")
			else:
				print(f"No data returned for {sensor_entity}, skipping channel2 update.")
		except Exception as e:
			print("Failed to edit channel2 with sensor data:", e)

@tasks.loop(time=coles_time)
async def coles_updates():
	print("Started coles_updates task")
	api_coles.try_bad_boys()

	build_id = api_coles.get_latest_build_id()
	browse_data = api_coles.fetch_category_structure(build_id)
	if not browse_data:
		print("Failed to get category structure")
		return
	categories = api_coles.extract_top_level_categories(browse_data)
	if not categories:
		print("No categories found")
		return

	print(f"Found {len(categories)} top-level categories")

	scraped_count = 0
	processed_categories = 0

	for i, category in enumerate(categories, 1):
		print(f"Processing category {i}/{len(categories)}: {category["name"]} (Products: {category["product_count"]})")

		try:
			products = api_coles.process_category(category, build_id)
			if products:
				save_path = api_coles.save_category_data(category, products, build_id)
				scraped_count += len(products)
				processed_categories += 1
				print(f"Processed {processed_categories}/{len(categories)} categories, total products scraped: {scraped_count}")
			else:
				print("No products saved for this category")
		except Exception as e:
			print(f"Error processing category {category["name"]}: {e}")
			

	print(f"Processed categories: {processed_categories}/{len(categories)}")
	print(f"Total products scraped: {scraped_count}")

	channel = discord_client.get_channel(int(os.getenv("COLES_UPDATES_CHANNEL")))

	file_data = api_coles.get_items_from_files("coles_data")
	all_items_raw = file_data["items"]
	invalid_file_ids = file_data["invalid_ids"]

	items_dict = {}
	for item in all_items_raw:
		item_id = item[0]
		items_dict[item_id] = item
	all_items = list(items_dict.values())
	print(f"Raw items: {len(all_items_raw)}, Deduplicated: {len(all_items)}")

	products = [str(item[0]) for item in all_items]

	active_ids = cursor.execute("SELECT id FROM coles_active_ids").fetchall()
	active_ids = [x[0] for x in active_ids]

	new_items = set(products) - {str(id) for id in active_ids}
	error_ids = cursor.execute("SELECT id FROM coles_error_ids").fetchall()
	error_ids = [x[0] for x in error_ids]

	if new_items:
		product_ids_int = [int(id_str) for id_str in new_items if int(id_str) not in error_ids]
		if product_ids_int:
			new_item_data = [item for item in all_items if item[0] in product_ids_int]
			for item in new_item_data:
				item_id = item[0]
				item_name = item[1]
				item_brand = item[2]
				await channel.send(f"[{item_brand} {item_name}](https://coles.com.au/product/{item_id}) was added to the database.")

			insert_data = [(id,) for id in product_ids_int]
			cursor.executemany("INSERT INTO coles_active_ids (id) VALUES (?)", insert_data)

	if invalid_file_ids:
		for item_id in invalid_file_ids:
			if item_id:
				cursor.execute("DELETE FROM coles_active_ids WHERE id = ?", (item_id,))
				await channel.send(f"Product ID {item_id} was removed from the database due to invalid data in files.")

	active_ids = cursor.execute("SELECT id FROM coles_active_ids").fetchall()
	active_ids = [x[0] for x in active_ids]

	if active_ids:
		placeholders = ",".join("?" * len(active_ids))

		latest_prices_query = f"""
			SELECT id, price 
			FROM coles_price_history 
			WHERE id IN ({placeholders})
			AND (id, date) IN (
				SELECT id, MAX(date) 
				FROM coles_price_history 
				WHERE id IN ({placeholders})
				GROUP BY id
			)
		"""
		latest_prices = cursor.execute(latest_prices_query, active_ids + active_ids).fetchall()
		latest_prices_dict = {item_id: price for item_id, price in latest_prices}

		max_prices_query = f"""
			SELECT id, MAX(CAST(price AS REAL)) as max_price
			FROM coles_price_history 
			WHERE id IN ({placeholders})
			GROUP BY id
		"""
		max_prices = cursor.execute(max_prices_query, active_ids).fetchall()
		max_prices_dict = {item_id: str(max_price) for item_id, max_price in max_prices}
	else:
		latest_prices_dict = {}
		max_prices_dict = {}

	insert_data = []

	for item in all_items:
		item_id = item[0]
		item_price = item[4]
		item_name = item[1]
		item_brand = item[2]
		item_image = item[9]

		if item_price == 0 or item_price == "0":
			print(f"WARNING: Zero price detected for item {item_id} ({item_brand} {item_name})")
			print(f"Raw item data: {item}")
			continue

		if item_id not in active_ids:
			continue

		if item_price is None:
			print(f"DEBUG: Skipping item {item_id} ({item_brand} {item_name}) due to None price")
			continue

		date = dt.now(pytz.timezone(timezone)).strftime("%Y-%m-%d %H:%M:%S")
		item_price = str(item_price)

		if item_price == "0":
			print(f"WARNING: Price became zero after string conversion for item {item_id}")
			print(f"Original price value: {item[4]}")
			continue

		db_price = latest_prices_dict.get(item_id)
		if db_price is None:
			print(f"DEBUG: Inserting new price history record: id={item_id}, price={item_price}, date={date}")
			insert_data.append((item_id, item_price, date))
			continue

		max_price = max_prices_dict.get(item_id)
		if db_price != item_price:
			insert_data.append((item_id, item_price, date))
			if max_price and float(item_price) > float(max_price):
				await channel.send(f"[{item_brand} {item_name}](https://coles.com.au/product/{item_id}) reached an all-time high: ${str(max_price)} -> ${str(item_price)} ({helpers.percentage_change(float(max_price), float(item_price))}).")
				price_history_document = {
					"item_brand": item_brand,
					"item_name": item_name,
					"item_id": item_id,
					"image_url": item_image,
					"price_before": float(max_price),
					"price_after": float(item_price),
					"date": dt.now(pytz.timezone(timezone))
				}
				try:
					await coles_updates_collection.insert_one(price_history_document)
					print(f"Inserted price history for item_id: {item_id}")
				except Exception as e:
					print(f"Error inserting into MongoDB: {e}")

	if insert_data:
		cursor.executemany(
			"INSERT INTO coles_price_history (id, price, date) VALUES (?, ?, ?)", 
			insert_data
		)
		print(f"Inserted {len(insert_data)} new records into the price history.")
	
	coles_data_folder = "coles_data"
	if os.path.exists(coles_data_folder):
		shutil.rmtree(coles_data_folder)
		print(f"Deleted contents of {coles_data_folder} folder.")
	else:
		print(f"{coles_data_folder} folder does not exist.")

	print("Finished coles_updates task")

kfc_last_token_refresh = None
kfc_refresh_fail_count = 0

@tasks.loop(minutes=30, reconnect=True)
async def kfc_deals_bg():
	global kfc_last_token_refresh, kfc_refresh_fail_count
	try:
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS kfc_deals (
				deal_id TEXT PRIMARY KEY,
				title TEXT,
				posted_at TEXT
			)
		""")
		
		channel = discord_client.get_channel(int(os.getenv("BANGERS_CHANNEL")))
		
		current_time = dt.now()
		should_refresh = (
			kfc_last_token_refresh is None or
			(current_time - kfc_last_token_refresh).total_seconds() > 3000
		)
		print(f"[{current_time.isoformat()}] kfc_deals_bg start: fail_count={kfc_refresh_fail_count}, last_refresh={kfc_last_token_refresh}")

		if should_refresh:
			try:
				token_refreshed = await api_kfc.refresh_token()
				if token_refreshed:
					kfc_last_token_refresh = current_time
					kfc_refresh_fail_count = 0
					print(f"[{current_time.isoformat()}] KFC token refreshed successfully")
				else:
					kfc_refresh_fail_count += 1
					print(f"[{current_time.isoformat()}] KFC token refresh returned nothing (fail #{kfc_refresh_fail_count})")
			except Exception as e:
				kfc_refresh_fail_count += 1
				print(f"[{current_time.isoformat()}] Failed to refresh KFC token (fail #{kfc_refresh_fail_count}): {type(e).__name__}: {e}")

		deals = await api_kfc.get_kfc_deals()
		if not deals:
			print("No KFC deals found")
			return
		
		posted_deals = cursor.execute("SELECT deal_id FROM kfc_deals").fetchall()
		posted_deal_ids = [deal[0] for deal in posted_deals]
		
		new_deals = [deal for deal in deals if deal["deal_id"] not in posted_deal_ids]
		
		if len(new_deals) == 0:
			print("No new KFC deals to post")
			return
		
		print(f"Found {len(new_deals)} new KFC deals to post")
		
		for deal in new_deals:
			try:
				embed = discord.Embed(
					title=deal["title"],
					description=deal["description"],
					color=0xCC0000
				)
				
				if deal.get("image_url"):
					embed.set_image(url=deal["image_url"])
				
				embed.add_field(
					name="Available",
					value=f"Starts: {deal["start_date"]}\nEnds: {deal["end_date"]}",
					inline=False
				)
				
				embed.add_field(
					name="Redemptions",
					value=f"Redeemed {deal["global_redeems"]} times",
					inline=False
				)
				
				await channel.send(embed=embed)
				
				cursor.execute(
					"INSERT INTO kfc_deals (deal_id, title, posted_at) VALUES (?, ?, ?)",
					(deal["deal_id"], deal["title"], dt.now(pytz.timezone(timezone)).strftime("%Y-%m-%d %H:%M:%S"))
				)
				
				print(f"Posted KFC deal: {deal["title"]}")
			except Exception as e:
				print(f"Error posting KFC deal '{deal.get("title", "Unknown")}': {e}")
	
	except Exception as e:
		print(f"KFC deals task encountered an exception: {e}.\nWill reconnect automatically.")
