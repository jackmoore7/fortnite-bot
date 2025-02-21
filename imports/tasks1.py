import os
import requests
import discord
import uuid
import asyncio
import feedparser
import imghdr
import pytz
import re

from datetime import datetime as dt, timedelta
from datetime import time
from time import mktime
from discord.ext import tasks
from PIL import Image
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from imports.core_utils import discord_client, cursor, tasks_list, mongo_client
from imports.api import api_openai
import imports.helpers as helpers
import imports.api.api_third_party as api_third_party
import imports.api.api_epic as api_epic
import imports.api.api_coles as api_coles
import imports.api.api_lego as api_lego
import imports.uv as uv
import imports.api.api_seveneleven as api_seveneleven

mongo_db = mongo_client['coles']
coles_updates_collection = mongo_db['coles_updates']

start_time = time(20, 1, 0)
end_time = time(7, 0, 0)
time_list = [time(hour, minute) for hour in range(start_time.hour, 24) for minute in range(0, 60, 1)] + [time(hour, minute) for hour in range(end_time.hour + 1) for minute in range(0, 60, 1)]
coles_time = [time(19, 0)]

async def tasks_on_ready():
	await discord_client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="me booty arrrr"))
	if not fortnite_update_bg.is_running():
		fortnite_update_bg.start()
	if not tv_show_update_bg.is_running():
		tv_show_update_bg.start()
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
	if not gog_free_games.is_running():
		gog_free_games.start()
	if not lego_bg.is_running():
		lego_bg.start()
	if not fuel_check.is_running():
		fuel_check.start()
	if not fortnite_shop_update_v3.is_running():
		fortnite_shop_update_v3.start()
	if not coles_updates.is_running():
		coles_updates.start()
	tasks_list["update"] = fortnite_update_bg
	tasks_list["tv"] = tv_show_update_bg
	tasks_list["status"] = fortnite_status_bg
	tasks_list["coles"] = coles_specials_bg
	tasks_list["arpansa"] = arpansa
	tasks_list['free_games'] = epic_free_games
	tasks_list['ozb_bangers'] = ozb_bangers
	tasks_list['lego'] = lego_bg
	tasks_list['shop'] = fortnite_shop_update_v3
	print(f"{discord_client.user} is online! My PID is {os.getpid()}.")

@tasks.loop(time=time_list)
async def arpansa():
	try:
		ch = discord_client.get_channel(int(os.getenv('UV_CHANNEL')))
		role = os.getenv('SUNSCREEN_ROLE')
		current_date = dt.now(helpers.timezone).strftime('%Y-%m-%d')
		current_time = (dt.now(helpers.timezone)-timedelta(minutes=1)).strftime('%H:%M')
		db_date = cursor.execute("SELECT start FROM uv_times").fetchone()[0]
		data = uv.get_arpansa_data()
		current_uv = float(data['CurrentUVIndex'])
		max_uv_today_recorded = float(data['MaximumUVLevel'])
		max_uv_today_recorded_time = data['MaximumUVLevelDateTime'][-5:]
		r = data['GraphData']
		forecast_graph = [entry["Forecast"] for entry in data["GraphData"]]
		measured_graph = [entry["Measured"] for entry in data["GraphData"]]
		dates_graph = [dt.strptime(entry["Date"], "%Y-%m-%d %H:%M") for entry in data["GraphData"]]
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
		plt.savefig("uv_index_plot.png")
		plt.close()

		if db_date != current_date:
			print("It's a new day!")
			first_forecast_gte_3_item = next((item for item in r if item['Forecast'] >= 3), None)
			max_uv_today_forecast = max(r, key=lambda item: item['Forecast'])['Forecast']
			max_uv_today_forecast_time = max(r, key=lambda item: item['Forecast'])['Date'][-5:]
			embed = discord.Embed(color=0xa3c80a)
			if first_forecast_gte_3_item:
				first_forecast_lt_3_item = next((item for item in r[r.index(first_forecast_gte_3_item) + 1:] if item['Forecast'] < 3), None)
				embed.title = "Sun protection required today"
				# await ch.send(f"<@&{role}>")
				embed.add_field(name="Time", value=f"{first_forecast_gte_3_item['Date'][-5:]} - {first_forecast_lt_3_item['Date'][-5:]}", inline=False)
				cursor.execute("UPDATE uv_times SET safe = 0")
			else:
				embed.title = "No sun protection required today"
				cursor.execute("UPDATE uv_times SET safe = 1")
			embed.add_field(name="Maximum UV (Forecast)", value=f"{uv.calculate_emoji(max_uv_today_forecast)} {max_uv_today_forecast} at {max_uv_today_forecast_time}", inline=False)
			embed.add_field(name="Maximum UV (Recorded)", value=f"{uv.calculate_emoji(max_uv_today_recorded)} {max_uv_today_recorded} at {max_uv_today_recorded_time}", inline=False)
			embed.add_field(name="Current UV", value=f"{uv.calculate_emoji(current_uv)} {current_uv} at {current_time}", inline=False)
			msg = await ch.send(embed=embed)
			cursor.execute("UPDATE uv_times SET end = ?", (msg.id,))
			cursor.execute("UPDATE uv_times SET start = ?", (current_date,))

		msg = await ch.fetch_message(int(cursor.execute("SELECT end FROM uv_times").fetchone()[0]))
		emb = msg.embeds[0]
		emb.set_field_at(-1, name="Current UV", value=f"{uv.calculate_emoji(current_uv)} {current_uv} at {current_time}")
		emb.set_field_at(-2, name="Maximum UV (Recorded)", value=f"{uv.calculate_emoji(max_uv_today_recorded)} {max_uv_today_recorded} at {max_uv_today_recorded_time}", inline=False)
		emb.color = discord.Color(uv.calculate_hex(current_uv))
		file = discord.File("uv_index_plot.png", filename="uv_index_plot.png")
		emb.set_image(url="attachment://uv_index_plot.png")
		await msg.edit(embed=emb, file=file)

		await ch.edit(name=f"{uv.calculate_emoji(current_uv)} uv")

		safe = bool(cursor.execute("SELECT safe FROM uv_times").fetchone()[0])
		if safe and current_uv >= 3:
			await ch.send(f"<@&{role}> Earlier forecast was incorrect - UV index is now above safe levels. slip slop slap bitch")
			cursor.execute("UPDATE uv_times SET safe = 0")
	except Exception as e:
		print(f"ARPANSA task encountered an exception: {e}")
		await asyncio.sleep(60)
		arpansa.restart()

@tasks.loop(minutes=5)
async def fortnite_update_bg():
	try:
		channel = discord_client.get_channel(int(os.getenv('UPD8_CHANNEL')))
		response = api_epic.get_fortnite_update_manifest()
		current_version = cursor.execute("SELECT version FROM aes").fetchone()[0]
		if current_version != response:
			cursor.execute("UPDATE aes SET version = ?", (response,))
			embed = discord.Embed(title="A new Fortnite update was just deployed")
			embed.add_field(name="Build", value=response, inline=False)
			await channel.send("<@&" + os.getenv('UPD8_ROLE') + ">", embed=embed)
	except Exception as e:
		print("Something went wrong getting the Fortnite manifest: " + str(repr(e)) + "\nRestarting internal task in 1 minute.")
		await asyncio.sleep(60)
		fortnite_update_bg.restart()

@tasks.loop(minutes=5)
async def check_scheduled_maintenance():
    try:
        channel = discord_client.get_channel(int(os.getenv('UPD8_CHANNEL')))
        maintenances = api_epic.get_fortnite_maintenance()
        if not maintenances:
            return
        for maintenance in maintenances:
            maintenance_id = maintenance["id"]
            if cursor.execute("SELECT 1 FROM scheduled_maintenance WHERE id = ?", (maintenance_id,)).fetchone():
                continue
            utc_start = dt.fromisoformat(maintenance["scheduled_for"]).replace(tzinfo=pytz.utc)
            utc_end = dt.fromisoformat(maintenance["scheduled_until"]).replace(tzinfo=pytz.utc)
            sydney_start = int(utc_start.astimezone(pytz.timezone("Australia/Sydney")).timestamp())
            sydney_end = int(utc_end.astimezone(pytz.timezone("Australia/Sydney")).timestamp())
            start_time = f"<t:{sydney_start}:R>"
            end_time = f"<t:{sydney_end}:R>"
            embed = discord.Embed(title="Scheduled maintenance", description=maintenance["name"])
            embed.add_field(name="Starts", value=start_time, inline=False)
            embed.add_field(name="Ends (Sydney Time)", value=end_time, inline=False)
            await channel.send("<@&" + os.getenv('UPD8_ROLE') + ">", embed=embed)
            cursor.execute("INSERT INTO scheduled_maintenance (id) VALUES (?)", (maintenance_id,))
    except Exception as e:
        print(f"Error checking maintenance: {repr(e)}\nRestarting task in 3 minutes.")
        await asyncio.sleep(180)
        check_scheduled_maintenance.restart()

@tasks.loop(minutes=5)
async def fortnite_status_bg():
	try:
		channel = discord_client.get_channel(int(os.getenv('UPD8_CHANNEL')))
		response = api_epic.get_fortnite_status()
		current_status = cursor.execute("SELECT * FROM server").fetchall()[0][0]
		if current_status != response:
			cursor.execute("UPDATE server SET status = ?", (response,))
			embed = discord.Embed(title = "Fortnite server status update")
			embed.add_field(name="Status", value=response)
			await channel.send("<@&" + os.getenv('UPD8_ROLE') + ">", embed=embed)
	except Exception as e:
		print("Something went wrong getting the Fortnite status: " + str(repr(e)) + "\nRestarting internal task in 3 minutes.")
		await asyncio.sleep(180)
		fortnite_status_bg.restart()

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
					with open(f'temp_images/{new_uuid}.{img_type}', "wb") as f:
						f.write(img.content)
					image = Image.open(f'temp_images/{new_uuid}.{img_type}')
					image.verify()
					print(f"{new_uuid} was successfully downloaded and verified")
					return f"{new_uuid}.{img_type}"
				except Exception as e:
					print(f"Broken image detected: {e}")
					os.remove(f'temp_images/{new_uuid}.{img_type}')
					if attempt < max_retries - 1:
						print(f"Retrying ({attempt + 1}/{max_retries})...")
					else:
						print(f"Max retries reached, failed to download {new_uuid}")
						no_images.append(name)
						break
		else:
			no_images.append(name)

	channel = discord_client.get_channel(int(os.getenv('SHOP2_CHANNEL')))
	r = api_third_party.fortnite_shop_v3()
	date = cursor.execute("SELECT date FROM shop_v3").fetchone()[0]
	new_date = r['data']['date']
	if new_date != date:
		vbucks_emoji = discord_client.get_emoji(int(os.getenv('VBUCKS_EMOJI')))
		ping_list = cursor.execute("SELECT item, id FROM shop_ping").fetchall()
		no_images = []
		daily = []
		for item in r['data']['daily']:
			if isinstance(item['history'], bool) or (item['history'].get('dates') and len(item['history']['dates']) < 2):
				if 'featured' in item['images'] and item['images']['featured']:
					daily.append((item['images']['featured'], item['name'], item['history'], item['price']))
				elif 'icon' in item['images'] and item['images']['icon']:
					daily.append((item['images']['icon'], item['name'], item['history'], item['price']))
				else:
					no_images.append((item['name'], item['history'], item['price']))
			else:
				if 'featured' in item['images'] and item['images']['featured']:
					daily.append((item['images']['featured'], item['name'], sorted(item['history']['dates'])[-2], item['price']))
				elif 'icon' in item['images'] and item['images']['icon']:
					daily.append((item['images']['icon'], item['name'], sorted(item['history']['dates'])[-2], item['price']))
				else:
					no_images.append((item['name'], sorted(item['history']['dates'])[-2], item['price']))
		featured = []
		for item in r['data']['featured']:
			if isinstance(item['history'], bool) or (item['history'].get('dates') and len(item['history']['dates']) < 2):
				if 'featured' in item['images'] and item['images']['featured']:
					featured.append((item['images']['featured'], item['name'], item['history'], item['price']))
				elif 'icon' in item['images'] and item['images']['icon']:
					featured.append((item['images']['icon'], item['name'], item['history'], item['price']))
				else:
					no_images.append((item['name'], item['history'], item['price']))
			else:
				if 'featured' in item['images'] and item['images']['featured']:
					featured.append((item['images']['featured'], item['name'], sorted(item['history']['dates'])[-2], item['price']))
				elif 'icon' in item['images'] and item['images']['icon']:
					featured.append((item['images']['icon'], item['name'], sorted(item['history']['dates'])[-2], item['price']))
				else:
					no_images.append((item['name'], sorted(item['history']['dates'])[-2], item['price']))
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
			await channel.send(f"{item[1]} - Last seen {helpers.timestampify_z(item[2])}", file=discord.File(f'temp_images/{img}'))
			os.remove(f'temp_images/{img}')
		for item in diff:
			img = process_image(item[0], item[1])
			matching_items = [i for i, u in ping_list if i.lower() in item[1].lower()]
			for cosmetic in matching_items:
				users = [u for i, u in ping_list if i == cosmetic]
				for user in users:
					await channel.send(f"<@{user}>, {item[1]} is in the shop\nTriggered by your keyword: {cosmetic}")
			if isinstance(item[2], (bool, dict)):
				await channel.send(f"## {item[1]} - {item[3]} {vbucks_emoji}\nFirst appearance in the shop!", file=discord.File(f'temp_images/{img}'))
			else:
				await channel.send(f"## {item[1]} - {item[3]} {vbucks_emoji}\nLast seen: {helpers.timestampify_z(item[2])}", file=discord.File(f'temp_images/{img}'))
			os.remove(f'temp_images/{img}')
		if no_images:
			await channel.send("The following items did not have associated images or failed to download after multiple attempts:")
			for item in no_images:
				await channel.send(item)
		cursor.execute("DELETE FROM shop_v3_content")
		cursor.executemany("INSERT INTO shop_v3_content VALUES (?, ?)", [(item[0], item[1]) for item in featured])
		cursor.execute("UPDATE shop_v3 SET date = ?", (date,))

@tasks.loop(minutes=180)
async def coles_specials_bg():
	try:
		channel = discord_client.get_channel(int(os.getenv('COLES_SPECIALS_CHANNEL')))
		product_url = "https://www.coles.com.au/product/"
		items = cursor.execute("SELECT * FROM coles_specials").fetchall()
		item_ids = cursor.execute("SELECT id FROM coles_specials").fetchall()
		item_ids_list = []
		for id in item_ids:
			item_ids_list.append(id[0])
		results = api_coles.get_items(item_ids_list)
		invalid_ids = results['invalid_ids']
		if len(invalid_ids) > 0:
			await channel.send("Couldn't find any products with these IDs: " + str(invalid_ids))
		results = results['items']
		items_new = []
		for item in results:
			items_new.append(item)
		if items != items_new:
			for item in items_new:
				cursor.execute("UPDATE coles_specials SET available = ?, on_sale = ?, current_price = ? WHERE id = ?", (item[6], item[5], item[4], item[0]))
		for item1, item2 in zip(items, items_new):
			differences_exist = any(old_value != new_value for old_value, new_value in zip(item1[4:], item2[4:]))
			if differences_exist:
				embed = discord.Embed(title=f"{item2[2]} {item2[1]}", url=product_url + str(item2[0]), color=0xe01a22)
				embed.set_thumbnail(url=item2[9])
				field_names = ['Price', 'Promotion', 'Available']
				for name, old_value, new_value in zip(field_names, item1[4:], item2[4:]):
					if name == 'Price':
						# if old_value != new_value:
						# 	cursor.execute("INSERT INTO coles_price_history (id, price, date) VALUES (?, ?, ?)", (item2[0], item2[4], dt.now(pytz.timezone('Australia/Sydney')).strftime('%Y-%m-%d %H:%M:%S')))
						if new_value is None:
							field_value = f"~~${old_value}~~\nPrice not specified"
						else:
							field_value = f"~~${old_value}~~\n${float(new_value)} ({helpers.percentage_change(old_value, new_value)})" if old_value != new_value else f"${new_value}"
					elif name == 'Promotion' and item2[10]:
						field_value = f"~~{bool(old_value)}~~\n{new_value} ({item2[10]})" if old_value != new_value else f"{new_value} ({item2[10]})"
					else:

						field_value = f"~~{bool(old_value)}~~\n{new_value}" if old_value != new_value else new_value
					embed.add_field(name=name, value=field_value, inline=False)
				if item2[7]:
					field_value = f"{item2[7]} - reduces the price per unit to ${item2[8]}" if item2[8] else f"{item2[7]}"
					embed.add_field(name='Promotion details', value=field_value, inline=False)
				embed.add_field(name='Recommendation', value=api_openai.coles_recommendation(item2[0], item2[4], dt.now(pytz.timezone('Australia/Sydney')).strftime('%Y-%m-%d %H:%M:%S')), inline=False)
				await channel.send(embed=embed)
	except Exception as e:
		await channel.send("Something went wrong getting item details from Coles: " + str(repr(e)) + "\nRestarting internal task in 3 hours")
		await asyncio.sleep(10800)
		coles_specials_bg.restart()

@tasks.loop(minutes=30)
async def lego_bg():
	# try:
		channel = discord_client.get_channel(int(os.getenv('LEGO_CHANNEL')))
		product_url = 'https://www.lego.com/en-au/product/'
		items_old = cursor.execute("SELECT * FROM lego").fetchall()
		items_new = []
		for item in items_old:
			result = api_lego.get_lego_item_by_id(item[0])
			if result:
				result = result['data']['product']
				product_code = int(result['productCode'])
				name = result['name']
				image_url = result['baseImgUrl']
				slug = result['slug']
				availability = result['variant']['attributes']['availabilityText']
				on_sale = result['variant']['attributes']['onSale']
				price = result['variant']['price']['formattedAmount']
				items_new.append((product_code, name, image_url, slug, availability, on_sale, price))

		if items_old != items_new:
			for item in items_new:
				cursor.execute("UPDATE lego SET name = ?, image_url = ?, slug = ?, availability = ?, on_sale = ?, price = ? WHERE id = ?", (item[1], item[2], item[3], item[4], item[5], item[6], item[0]))

		for item1, item2 in zip(items_old, items_new):
			differences_exist = any(old_value != new_value for old_value, new_value in zip(item1[3:], item2[3:]))

			if differences_exist:
				embed = discord.Embed(title=item2[1], url=product_url + item2[3])
				embed.set_thumbnail(url=item2[2])

				field_names = ['Availability', 'On sale', 'Price']

				for name, old_value, new_value in zip(field_names, item1[4:], item2[4:]):
					field_value = f"~~{old_value}~~\n{new_value}" if old_value != new_value else new_value
					embed.add_field(name=name, value=field_value, inline=False)

				await channel.send(embed=embed)

	# except Exception as e:
	# 	await channel.send(f"Exception: {e}")

@tasks.loop(minutes=60)
async def epic_free_games():
	
	ch = discord_client.get_channel(int(os.getenv('FREE_GAMES_CHANNEL')))

	def timestampify_and_convert_to_aest(string):
		utc_timezone = pytz.timezone('UTC')
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
		utc_timezone = pytz.timezone('UTC')
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
			await ch.send(f"<@&{os.getenv('FREE_GAMES_ROLE')}>", embed=embed)
			cursor.execute("INSERT INTO free_games VALUES (?, ?, ?, ?)", (game[0], game[1], game[2], convert_to_aest(game[4])))
	
	for game in posted:
		if test_time(game[3]):
			cursor.execute("DELETE FROM free_games WHERE title = ?", (game[0],))
			print(f"{game[0]} was deleted from the free_games database as the promotional period has ended.")

@tasks.loop(minutes=60)
async def gog_free_games():
	ch = discord_client.get_channel(int(os.getenv('FREE_GAMES_CHANNEL')))
	posted = cursor.execute("SELECT * FROM gog_free_games").fetchall()
	r = requests.get("https://www.gog.com/")
	soup = BeautifulSoup(r.content, 'html.parser')
	giveaway = soup.find('a', {'id': 'giveaway'})
	if giveaway:
		href = giveaway.get('ng-href')
		url = f"https://gog.com{href}"
		if url not in [x[0] for x in posted]:
			timestamp = giveaway.find_next('div', {'class': 'giveaway-banner--with-consent__content'}).find('div', {'class': 'giveaway-banner__footer'}).find('gog-countdown-timer')
			if timestamp:
				timestamp = f"<t:{int(timestamp['end-date'])//1000}:R>"
			else:
				timestamp = "Unknown"
			embed = discord.Embed()
			embed.title = "New free game on GOG"
			embed.description = url
			embed.add_field(name="Ends", value=timestamp)
			await ch.send(f"<@&{os.getenv('FREE_GAMES_ROLE')}>", embed=embed)
			cursor.execute("INSERT INTO gog_free_games VALUES (?)", (url,))
	else:
		cursor.execute("DELETE FROM gog_free_games")

@tasks.loop(minutes=30)
async def tv_show_update_bg():
	try:
		user = discord_client.get_user(int(os.getenv('ME')))
		url = os.getenv('SHOWRSS')
		feed = feedparser.parse(url)
		last_guid = cursor.execute("select * from rss").fetchall()[0][0]
		if len(feed['entries']) > 0:
			latest_guid = feed['entries'][0]['guid']
		else:
			return
		if latest_guid != last_guid:
			rssembed = discord.Embed(title = "A new episode just released!")
			rssembed.add_field(name="Name", value=feed['entries'][0]['tv_raw_title'], inline=False)
			rssembed.add_field(name="Released", value=feed['entries'][0]['published'], inline=False)
			cursor.execute("UPDATE rss SET guid = ?", (latest_guid,))
			await user.send(embed = rssembed)
	except Exception as e:
		print("Something went wrong getting the TV show RSS: " + str(repr(e)) + "\nRestarting internal task in 1 minute.")
		await asyncio.sleep(60)
		tv_show_update_bg.restart()

@tasks.loop(minutes=10)
async def ozb_bangers():
	try:
		feed = feedparser.parse("https://www.ozbargain.com.au/deals/feed")
		posted = cursor.execute("SELECT * FROM ozbargain").fetchall()
		for post in feed['entries']:
			upvotes = int(post['ozb_meta']['votes-pos'])
			downvotes = int(post['ozb_meta']['votes-neg'])
			clicks = int(post['ozb_meta']['click-count'])
			try:
				prefix = f"[{post['ozb_title-msg']['type'].upper()}]"
			except Exception:
				prefix = ''
			if (upvotes >= 250 and downvotes < 10) and (post['link'] not in [x[0] for x in posted]) and (prefix != '[EXPIRED]'):
				try:
					expiry = helpers.timestampify(post['ozb_meta']['expiry'])
				except Exception:
					expiry = "Unknown"
				title = post['title']
				link = post['link']
				upvote_emoji = discord_client.get_emoji(int(os.getenv('UPVOTE_EMOJI')))
				downvote_emoji = discord_client.get_emoji(int(os.getenv('DOWNVOTE_EMOJI')))
				ch = discord_client.get_channel(int(os.getenv('OZB_BANGERS_CHANNEL')))
				embed = discord.Embed()
				embed.title = f"{prefix} {title}"
				embed.description = f"{upvote_emoji} >={upvotes}\n{downvote_emoji} {downvotes}\nClicks: {clicks}"
				try:
					if post['ozb_meta']['image']:
						embed.set_image(url=post['ozb_meta']['image'])
				except:
					print("No image associated with this banger.")
				embed.add_field(name="Link", value=link, inline=False)
				embed.add_field(name="Expires", value=expiry, inline=False)
				await ch.send(embed=embed)
				cursor.execute("INSERT INTO ozbargain VALUES (?)", (link,))
	except Exception as e:
		print(f"ozb_bangers encountered an exception: {e}")
		await asyncio.sleep(60)
		ozb_bangers.restart()

@tasks.loop(minutes=5)
async def fuel_check():
	channel = discord_client.get_channel(int(os.getenv('FUEL_CHANNEL')))
	try:
		response = api_seveneleven.check_lowest_fuel_price_p03()
		# last_updated = response[1]
		response = response[0]
		db_price = cursor.execute("SELECT * FROM fuel").fetchone()[0]
		if db_price != str(response['price']):
			cursor.execute("UPDATE fuel SET price = ?", (str(response['price']),))
			await channel.send(f"The cheapest fuel is {response['type']} at {response['suburb']} for {response['price']}.")
	except Exception as e:
		# await channel.send(f"Uh oh {e}")
		print(f"fuel loop encountered an exception: {e}")

@tasks.loop(time=coles_time)
async def coles_updates():
	print("Started coles_updates task")
	api_coles.try_bad_boys()
	channel = discord_client.get_channel(int(os.getenv('COLES_UPDATES_CHANNEL')))
	headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
	namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
	pattern = re.compile(r'(\d+)$')

	def get_product_sitemap_urls():
		url = os.getenv('COLES_SITEMAP_URL')
		urls = []

		response = requests.get(url, headers=headers)
		if response.status_code == 200:
			with open('output.xml', 'wb') as f:
				f.write(response.content)
			tree = ET.parse('output.xml')
			root = tree.getroot()
			loc_elements = root.findall('.//ns:loc', namespace)
			for loc in loc_elements:
				urls.append(loc.text)
			return urls
		else:
			return response.status_code
		

	def get_products_from_urls(urls):
		files_list = []
		for url in urls:
			index = urls.index(url)
			files_list.append(f"output{index}.xml")
			response = requests.get(url, headers=headers)
			if response.status_code == 200:
				with open(f'output{index}.xml', 'wb') as f:
					f.write(response.content)
			else:
				return response.status_code
		return files_list


	sitemap_urls = get_product_sitemap_urls()

	files = get_products_from_urls(sitemap_urls)

	# files = ['output0.xml', 'output1.xml']

	products = []

	for file in files:
		tree = ET.parse(file)
		root = tree.getroot()


		for url_element in root.findall('ns:url', namespace):
			product_url = url_element.find('ns:loc', namespace).text
			match = pattern.search(product_url)
			if match:
				product_id = match.group(1)
				products.append(product_id)

	active_ids = cursor.execute("SELECT id FROM coles_active_ids").fetchall()
	active_ids = [x[0] for x in active_ids]

	new_items = set(products) - {str(id) for id in active_ids}
	error_ids = cursor.execute("SELECT id FROM coles_error_ids").fetchall()
	error_ids = [x[0] for x in error_ids]

	if new_items:
		product_ids_int = [int(id_str) for id_str in new_items if int(id_str) not in error_ids]
		if product_ids_int:
			results = api_coles.get_items(product_ids_int)
			for item in results['items']:
					item_id = item[0]
					item_name = item[1]
					item_brand = item[2]
					await channel.send(f"[{item_brand} {item_name}](https://coles.com.au/product/{item_id}) was added to the database.")
			insert_data = [(id,) for id in product_ids_int]
			cursor.executemany("INSERT INTO coles_active_ids (id) VALUES (?)", insert_data)

	active_ids = cursor.execute("SELECT id FROM coles_active_ids").fetchall()
	active_ids = [x[0] for x in active_ids]

	batch_size = 350
	insert_data = []

	for i in range(0, len(active_ids), batch_size):
		batch = active_ids[i:i+batch_size]
		results = api_coles.get_items(batch)
		if results:
			if len(results['invalid_ids']) > 0:
				for item in results['invalid_ids']:
					cursor.execute("DELETE FROM coles_active_ids WHERE id = ?", (item['id'],))
					await channel.send(f"[{item_brand} {item_name}](https://coles.com.au/product/{item['id']}) was deleted from the database because its ID returned invalid.")
			for item in results['items']:
				item_id = item[0]
				item_price = item[4]
				item_name = item[1]
				item_brand = item[2]
				item_image = item[9]
				
				if item_price is None:
					# cursor.execute("DELETE FROM coles_active_ids WHERE id = ?", (item_id,))
					# print(f"{item_id} was removed from the database as there was no price data.")
					# await channel.send(f"https://coles.com.au/product/{item_id} was discontinued.")
					continue

				date = dt.now(pytz.timezone('Australia/Sydney')).strftime('%Y-%m-%d %H:%M:%S')
				item_price = str(item_price)
				
				db_price = cursor.execute("SELECT price FROM coles_price_history WHERE id = ? ORDER BY date DESC LIMIT 1",(item_id,)).fetchone()
				if db_price is None:
					insert_data.append((item_id, item_price, date))
					continue
				
				max_price = cursor.execute("SELECT price FROM coles_price_history WHERE id = ? ORDER BY CAST(price AS REAL) DESC LIMIT 1", (item_id,)).fetchone()[0]
				if db_price[0] != item_price:
					insert_data.append((item_id, item_price, date))
					if float(item_price) > float(max_price):
						await channel.send(f"[{item_brand} {item_name}](https://coles.com.au/product/{item_id}) reached an all-time high: ${str(max_price)} -> ${str(item_price)} ({helpers.percentage_change(float(max_price), float(item_price))}).")
						price_history_document = {
							"item_brand": item_brand,
							"item_name": item_name,
							"item_id": item_id,
							"image_url": item_image,
							"price_before": float(max_price),
							"price_after": float(item_price),
							"date": dt.now(pytz.timezone('Australia/Sydney'))
						}
						try:
							await coles_updates_collection.insert_one(price_history_document)
							print(f"Inserted price history for item_id: {item_id}")
						except Exception as e:
							print(f"Error inserting into MongoDB: {e}")
		else:
			continue

	if insert_data:
		cursor.executemany(
			"INSERT INTO coles_price_history (id, price, date) VALUES (?, ?, ?)", 
			insert_data
		)
		print(f"Inserted {len(insert_data)} new records into the price history.")
	print("Finished coles_updates task")