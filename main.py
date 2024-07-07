import os
import sys
import requests
import shutil
import discord
import re
import uuid
import asyncio
import feedparser
from datetime import datetime as dt, timedelta
from datetime import time
from time import mktime
from discord.ext import tasks
from discord.ext.pages import Paginator, Page
from discord.ui import Button, View
import sqlite3 as sl
from dotenv import load_dotenv
import imghdr
import faulthandler, signal
from PIL import Image
from bs4 import BeautifulSoup
import logging
from systemd.journal import JournalHandler
import heartrate

heartrate.trace(browser=True, host='0.0.0.0')

log = logging.getLogger('demo')
log.addHandler(JournalHandler())
log.setLevel(logging.INFO)
log.info('sent to journal')

logging.basicConfig(level=logging.INFO)

faulthandler.enable(file=open('error.log', 'w'))
faulthandler.register(signal.SIGUSR1.value)

load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=os.getenv('GOOGLE_KEY')

from gcloud import *
from third_party_api import *
from key_handling import *
from epic_api import *
from coles import *
from uv import *
from openai_api import *
from lego_api import *
from ephemeral_port import *
from seveneleven_api import *

intents = discord.Intents.all()
intents.members = True

discordClient = discord.Bot(intents=intents)

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

tasks_list = {}

def timestampify(string):
	date_time_obj = dt.strptime(string, '%Y-%m-%dT%H:%M:%S%z')
	struct_time = date_time_obj.timetuple()
	return f"<t:{int(mktime(struct_time))}:R>"

def timestampify_z(string):
	date_time_obj = dt.strptime(string, '%Y-%m-%dT%H:%M:%S.%fZ')
	struct_time = date_time_obj.timetuple()
	return f"<t:{int(mktime(struct_time))}:R>"

def embed_tweets(message):
    url_regex = re.compile(r'https?:\/\/(?:www\.)?(twitter|x)\.com\/(?:#!\/)?(\w+)\/status(?:es)?\/(\d+)')
    replacement_regex = r'https://fxtwitter.com/\2/status/\3'
    match = url_regex.search(message.content)
    if match:
        url = match.group(0)
        modified_url = re.sub(url_regex, replacement_regex, url)
        modified_text = message.content.replace(url, modified_url)
        return modified_text

def percentage_change(old, new):
    try:
        change = new - old
        relative_change = change / abs(old)
        percentage_change = relative_change * 100
        formatted_percentage_change = f"{percentage_change:.2f}%"
        if percentage_change > 0:
            formatted_percentage_change = "+" + formatted_percentage_change
        return formatted_percentage_change
    except ZeroDivisionError:
        return "inf%"

@discordClient.event
async def on_ready():
	await discordClient.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="me booty arrrr"))
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
	if not transmission_port_forwarding.is_running():
		transmission_port_forwarding.start()
	if not fuel_check.is_running():
		fuel_check.start()
	if not fortnite_shop_update_v3.is_running():
		fortnite_shop_update_v3.start()
	tasks_list["update"] = fortnite_update_bg
	tasks_list["tv"] = tv_show_update_bg
	tasks_list["status"] = fortnite_status_bg
	tasks_list["coles"] = coles_specials_bg
	tasks_list["arpansa"] = arpansa
	tasks_list['free_games'] = epic_free_games
	tasks_list['ozb_bangers'] = ozb_bangers
	tasks_list['lego'] = lego_bg
	tasks_list['transmission'] = transmission_port_forwarding
	tasks_list['shop'] = fortnite_shop_update_v3
	print(f"{discordClient.user} is online! My PID is {os.getpid()}.")

@tasks.loop(minutes=5)
async def fortnite_update_bg():
	try:
		channel = discordClient.get_channel(int(os.getenv('UPD8_CHANNEL')))
		response = get_fortnite_update_manifest()
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

@tasks.loop(minutes=30)
async def tv_show_update_bg():
	try:
		user = discordClient.get_user(int(os.getenv('ME')))
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
		
@tasks.loop(minutes=180)
async def coles_specials_bg():
	try:
		channel = discordClient.get_channel(int(os.getenv('COLES_SPECIALS_CHANNEL')))
		product_url = "https://www.coles.com.au/product/"
		items = cursor.execute("SELECT * FROM coles_specials").fetchall()
		item_ids = cursor.execute("SELECT id FROM coles_specials").fetchall()
		item_ids_list = []
		for id in item_ids:
			item_ids_list.append(id[0])
		results = get_items(item_ids_list)
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
						field_value = f"~~${old_value}~~\n${float(new_value)} ({percentage_change(old_value, new_value)})" if old_value != new_value else f"${new_value}"
					elif name == 'Promotion' and item2[10]:
						field_value = f"~~{bool(old_value)}~~\n{new_value} ({item2[10]})" if old_value != new_value else f"{new_value} ({item2[10]})"
					else:
						field_value = f"~~{bool(old_value)}~~\n{new_value}" if old_value != new_value else new_value
					embed.add_field(name=name, value=field_value, inline=False)
				if item2[7]:
					field_value = f"{item2[7]} - reduces the price per unit to ${item2[8]}" if item2[8] else f"{item2[7]}"
					embed.add_field(name='Promotion details', value=field_value, inline=False)
				await channel.send(embed=embed)
	except Exception as e:
		await channel.send("Something went wrong getting item details from Coles: " + str(repr(e)) + "\nRestarting internal task in 3 hours")
		await asyncio.sleep(10800)
		coles_specials_bg.restart()

@tasks.loop(minutes=30)
async def lego_bg():
	# try:
		channel = discordClient.get_channel(int(os.getenv('LEGO_CHANNEL')))
		product_url = 'https://www.lego.com/en-au/product/'
		items_old = cursor.execute("SELECT * FROM lego").fetchall()
		items_new = []
		for item in items_old:
			result = get_lego_item_by_id(item[0])
			if result:
				result = result['data']['product']
				id = int(result['productCode'])
				name = result['name']
				image_url = result['baseImgUrl']
				slug = result['slug']
				availability = result['variant']['attributes']['availabilityText']
				on_sale = result['variant']['attributes']['onSale']
				price = result['variant']['price']['formattedAmount']
				items_new.append((id, name, image_url, slug, availability, on_sale, price))

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

@tasks.loop(minutes=5)
async def fortnite_status_bg():
	try:
		channel = discordClient.get_channel(int(os.getenv('UPD8_CHANNEL')))
		response = get_fortnite_status()
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

	channel = discordClient.get_channel(int(os.getenv('SHOP2_CHANNEL')))
	r = fortnite_shop_v3()
	date = cursor.execute("SELECT date FROM shop_v3").fetchone()[0]
	new_date = r['data']['date']
	if new_date != date:
		vbucks_emoji = discordClient.get_emoji(int(os.getenv('VBUCKS_EMOJI')))
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
			await channel.send(f"{item[1]} - Last seen {timestampify_z(item[2])}", file=discord.File(f'temp_images/{img}'))
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
				await channel.send(f"## {item[1]} - {item[3]} {vbucks_emoji}\nLast seen: {timestampify_z(item[2])}", file=discord.File(f'temp_images/{img}'))
			os.remove(f'temp_images/{img}')
		if no_images:
			await channel.send("The following items did not have associated images or failed to download after multiple attempts:")
			for item in no_images:
				await channel.send(item)
		cursor.execute("DELETE FROM shop_v3_content")
		cursor.executemany("INSERT INTO shop_v3_content VALUES (?, ?)", [(item[0], item[1]) for item in featured])
		cursor.execute("UPDATE shop_v3 SET date = ?", (date,))

@tasks.loop(minutes=60)
async def epic_free_games():
	
	ch = discordClient.get_channel(int(os.getenv('FREE_GAMES_CHANNEL')))

	def timestampify_and_convert_to_aest(string):
		utc_timezone = pytz.timezone('UTC')
		sydney_timezone = pytz.timezone('Australia/Sydney')
		date_time_obj = dt.strptime(string, '%Y-%m-%dT%H:%M:%S.%fZ')
		date_time_obj = utc_timezone.localize(date_time_obj)
		sydney_time = date_time_obj.astimezone(sydney_timezone)
		struct_time = sydney_time.timetuple()
		timestamp = f"<t:{int(mktime(struct_time))}:R>"
		return timestamp

	def test_time(string):
		sydney_timezone = pytz.timezone('Australia/Sydney')
		end_dt = dt.strptime(string, '%Y-%m-%dT%H:%M:%S.%fZ')
		end_dt = sydney_timezone.localize(end_dt)
		current_dt = dt.now(sydney_timezone)
		if current_dt > end_dt:
			return True
		else:
			return False
		
	def convert_to_aest(string):
		utc_timezone = pytz.timezone('UTC')
		sydney_timezone = pytz.timezone('Australia/Sydney')
		date_time_obj = dt.strptime(string, '%Y-%m-%dT%H:%M:%S.%fZ')
		date_time_obj = utc_timezone.localize(date_time_obj)
		sydney_time = date_time_obj.astimezone(sydney_timezone)
		new_string = sydney_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
		return new_string

	games_list = get_free_games()
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
	ch = discordClient.get_channel(int(os.getenv('FREE_GAMES_CHANNEL')))
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

start_time = time(20, 1, 0)
end_time = time(7, 0, 0)
time_list = [time(hour, minute) for hour in range(start_time.hour, 24) for minute in range(0, 60, 1)] + [time(hour, minute) for hour in range(end_time.hour + 1) for minute in range(0, 60, 1)]

@tasks.loop(time=time_list)
async def arpansa():
	try:
		ch = discordClient.get_channel(int(os.getenv('UV_CHANNEL')))
		role = os.getenv('SUNSCREEN_ROLE')
		current_date = dt.now(pytz.timezone('Australia/Sydney')).strftime('%Y-%m-%d')
		current_time = (dt.now(pytz.timezone('Australia/Sydney'))-timedelta(minutes=1)).strftime('%H:%M')
		db_date = cursor.execute("SELECT start FROM uv_times").fetchone()[0]
		data = get_arpansa_data()
		current_uv = float(data['CurrentUVIndex'])
		max_uv_today_recorded = float(data['MaximumUVLevel'])
		max_uv_today_recorded_time = data['MaximumUVLevelDateTime'][-5:]
		r = data['GraphData']

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
			embed.add_field(name="Maximum UV (Forecast)", value=f"{calculate_emoji(max_uv_today_forecast)} {max_uv_today_forecast} at {max_uv_today_forecast_time}", inline=False)
			embed.add_field(name="Maximum UV (Recorded)", value=f"{calculate_emoji(max_uv_today_recorded)} {max_uv_today_recorded} at {max_uv_today_recorded_time}", inline=False)
			embed.add_field(name="Current UV", value=f"{calculate_emoji(current_uv)} {current_uv} at {current_time}", inline=False)
			msg = await ch.send(embed=embed)
			cursor.execute("UPDATE uv_times SET end = ?", (msg.id,))
			cursor.execute("UPDATE uv_times SET start = ?", (current_date,))

		msg = await ch.fetch_message(int(cursor.execute("SELECT end FROM uv_times").fetchone()[0]))
		emb = msg.embeds[0]
		emb.set_field_at(-1, name="Current UV", value=f"{calculate_emoji(current_uv)} {current_uv} at {current_time}")
		emb.set_field_at(-2, name="Maximum UV (Recorded)", value=f"{calculate_emoji(max_uv_today_recorded)} {max_uv_today_recorded} at {max_uv_today_recorded_time}", inline=False)
		emb.color = discord.Color(calculate_hex(current_uv))
		await msg.edit(embed=emb)

		await ch.edit(name=f"{calculate_emoji(current_uv)} uv")

		safe = bool(cursor.execute("SELECT safe FROM uv_times").fetchone()[0])
		if safe and current_uv >= 3:
			await ch.send(f"<@&{role}> Earlier forecast was incorrect - UV index is now above safe levels. slip slop slap bitch")
			cursor.execute("UPDATE uv_times SET safe = 0")
	except Exception as e:
		print(f"ARPANSA task encountered an exception: {e}")
		await asyncio.sleep(60)
		arpansa.restart()

@tasks.loop(minutes=10)
async def ozb_bangers():
	try:
		feed = feedparser.parse("https://www.ozbargain.com.au/deals/feed")
		posted = cursor.execute("SELECT * FROM ozbargain").fetchall()
		for post in feed['entries']:
			upvotes = int(post['ozb_meta']['votes-pos'])
			downvotes = int(post['ozb_meta']['votes-neg'])
			try:
				prefix = f"[{post['ozb_title-msg']['type'].upper()}]"
			except:
				prefix = ''
			if (upvotes >= 250 and downvotes < 10) and (post['link'] not in [x[0] for x in posted]) and (prefix != '[EXPIRED]'):
				try:
					expiry = timestampify(post['ozb_meta']['expiry'])
				except:
					expiry = "Unknown"
				title = post['title']
				link = post['link']
				upvote_emoji = discordClient.get_emoji(int(os.getenv('UPVOTE_EMOJI')))
				downvote_emoji = discordClient.get_emoji(int(os.getenv('DOWNVOTE_EMOJI')))
				ch = discordClient.get_channel(int(os.getenv('OZB_BANGERS_CHANNEL')))
				embed = discord.Embed()
				embed.title = f"{prefix} {title}"
				embed.description = f"{upvote_emoji} {upvotes}\n{downvote_emoji} {downvotes}"
				embed.set_image(url=post['ozb_meta']['image'])
				embed.add_field(name="Link", value=link, inline=False)
				embed.add_field(name="Expires", value=expiry, inline=False)
				await ch.send(embed=embed)
				cursor.execute("INSERT INTO ozbargain VALUES (?)", (link,))
	except Exception as e:
		print(f"ozb_bangers encountered an exception: {e}")
		await asyncio.sleep(60)
		ozb_bangers.restart()

@tasks.loop(minutes=5)
async def transmission_port_forwarding():
	try:
		channel = discordClient.get_channel(int(os.getenv('TRANSMISSION_CHANNEL')))
		response = test_port()
		if response:
			await channel.send(response)
	except Exception as e:
		await channel.send(f"transmission_port_forwarding encountered an exception: {e}")

@tasks.loop(minutes=5)
async def fuel_check():
	channel = discordClient.get_channel(int(os.getenv('FUEL_CHANNEL')))
	try:
		response = check_lowest_fuel_price_p03()
		last_updated = response[1]
		response = response[0]
		db_price = cursor.execute("SELECT * FROM fuel").fetchone()[0]
		if db_price != str(response['price']):
			cursor.execute("UPDATE fuel SET price = ?", (str(response['price']),))
			await channel.send(f"The cheapest fuel is {response['type']} at {response['suburb']} for {response['price']}.")
	except Exception as e:
		# await channel.send(f"Uh oh {e}")
		print(f"fuel loop encountered an exception: {e}")

coles = discordClient.create_group("coles", "Edit your tracked items list")

@coles.command(description="Search a Coles item by name")
async def search(ctx, string):
	await ctx.defer()
	results = search_item(string)
	if results:
		url = "https://productimages.coles.com.au/productimages"
		num_results = results['noOfResults']
		if num_results == 0:
			await ctx.respond("Your search returned no results.")
			return
		results = results['results']
		results_list = [(product['id'], product['name'], product['brand'], product['imageUris'][0]['uri']) for product in results if ('adId' not in product or not product['adId']) and 'id' in product]
		pages = []
		for item in results_list:
			embed = discord.Embed(
				title = f"{item[2]} {item[1]}"
			)
			embed.set_image(url=url + item[3])
			embed.add_field(name="ID", value=item[0])
			embed.set_footer(text=f"Returned {num_results} results")
			pages.append(Page(content=f"{item[2]} {item[1]}", embeds=[embed]))
		paginator = Paginator(pages=pages)
		await paginator.respond(ctx.interaction)
	else:
		await ctx.respond("Something went wrong. Please try again.")

@coles.command(description="[Owner] Add or remove an item")
async def edit(ctx, id):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		await ctx.defer()
		result = get_items([id])
		result = result['items'][0]
		if result:
			id = result[0]
			name = result[1]
			brand = result[2]
			description = result[3]
			current_price = result[4]
			on_sale = result[5]
			available = result[6]
			result_db = cursor.execute("SELECT * FROM coles_specials WHERE id = ?", (id,)).fetchone()
			if result_db:
				cursor.execute("DELETE FROM coles_specials WHERE id = ?", (id,))
				await ctx.respond(f"Removed {brand} {name} from your list")
			else:
				cursor.execute("INSERT INTO coles_specials VALUES (?, ?, ?, ?, ?, ?, ?)", (id, name, brand, description, current_price, on_sale, available))
				await ctx.respond(f"Added {brand} {name} to your list")
		else:
			await ctx.respond(result)

@coles.command(description="[Owner] View your tracked items")
async def list(ctx):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		try:
			tracked = cursor.execute("SELECT * FROM coles_specials")
			embed = discord.Embed(title = "Items you're tracking")
			for item in tracked:
				id = item[0]
				name = item[1]
				brand = item[2]
				current_price = item[4]
				on_sale = item[5]
				available = item[6]
				compact_info = f"**Brand**: {brand}\n**Price**: ${current_price}\n**On special**: {'Yes' if on_sale else 'No'}\n**Availability**: {'Available' if available else 'Unavailable'}"
				embed.add_field(name=f"{id} - {name}", value=compact_info, inline=False)
			await ctx.respond(embed=embed)
		except Exception as e:
			await ctx.respond(f"Couldn't get list: {e}")

@discordClient.slash_command(description="[Owner] Edit a message")
async def edit_message(ctx, id, content):
	try:
		if ctx.user.id != int(os.getenv('ME')):
			await ctx.respond("nice try bozo")
		else:
			channel = ctx.channel
			msg = await channel.fetch_message(id)
			await msg.edit(content=content)
			await ctx.respond("Edit successful.", ephemeral=True)

	except Exception as e:
		await ctx.respond(e, ephemeral=True)

@discordClient.slash_command(description="[Owner] Stop an internal task")
async def stop_task(ctx, task_name):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		try:
			task = tasks_list.get(task_name)
			if task:
				task.cancel()
				await ctx.respond(f"{task} stopped ✅")
			else:
				await ctx.respond(f"{task_name} not found.")
		except Exception as e:
			await ctx.respond(f"Task couldn't be stopped: {e}")

@discordClient.slash_command(description="[Owner] Add friend")
async def add_friend(ctx, user_id):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		e = add_friend(user_id)
		await ctx.respond(e)

@discordClient.slash_command(description="[Owner] List all friends")
async def list_friends(ctx, include_pending=''):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		e = get_all_friends(include_pending)
		await ctx.respond(e)

@discordClient.slash_command(description="Get Epic Games username by ID")
async def get_username(ctx, id):
	e = get_user_by_id(id)
	await ctx.respond(e['displayName'])

@discordClient.slash_command(description="Return when a user was last online")
async def get_last_online(ctx, username):
	await ctx.defer()
	id = getAccountID(username)
	await asyncio.sleep(3)
	e = get_user_presence(id)
	if e:
		await ctx.respond(f"{username} was last online at {e}")
	else:
		await ctx.respond("That user isn't in my friends list.")

@discordClient.slash_command(description="[Owner] Clear messages")
async def purge(ctx, amount):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
		return
	await ctx.defer()
	await ctx.channel.purge(limit=int(amount)+1, bulk=True)

@discordClient.slash_command(description="Get pinged for sun protection forecasts")
async def sunscreen(ctx):
	role = ctx.guild.get_role(int(os.getenv('SUNSCREEN_ROLE')))
	if not role:
		await ctx.respond("This command doesn't work in this server.")
		return
	if role in ctx.user.roles:
		await ctx.user.remove_roles(role)
		await ctx.respond("Removed ✅")
	else:
		await ctx.user.add_roles(role)
		await ctx.respond("Added ✅")

notifyme = discordClient.create_group("notifyme", "Get notified when an item you want is in the shop")

@notifyme.command(description="Add or remove a cosmetic")
async def edit(ctx, item):
	if len(item) > 25:
		await ctx.respond("String must be less than 26 characters")
		return
	text_check = re.findall(r'(?i)[^a-z0-9\s\-\']', item)
	if text_check:
		await ctx.respond("Not a valid string. [a-z0-9\s\-'] only.")
		return
	id = ctx.user.id
	if len(cursor.execute("SELECT * FROM shop_ping WHERE item = ? AND id = ?", (item, id)).fetchall()) > 0:
		cursor.execute("DELETE FROM shop_ping WHERE item = ? AND id = ?", (item, id))
		await ctx.respond("Removed ✅")
		return
	cursor.execute("INSERT INTO shop_ping VALUES (?, ?)", (id, item))
	await ctx.respond("Added ✅")

@notifyme.command(description="View the list of cosmetics you want notifications for")
async def list(ctx):
	items = cursor.execute("SELECT item FROM shop_ping WHERE id = ?", (ctx.user.id,)).fetchall()
	items = [item[0] for item in items]
	await ctx.respond(items)

@discordClient.slash_command(description="Subscribe/unsubscribe to Fortnite status updates")
async def update(ctx):
	upd8 = ctx.guild.get_role(int(os.getenv('UPD8_ROLE')))
	if upd8 in ctx.user.roles:
		await ctx.user.remove_roles(upd8)
		await ctx.respond("Removed ✅")
	else:
		await ctx.user.add_roles(upd8)
		await ctx.respond("Added ✅")

@discordClient.slash_command(description="Check a user's all-time Fortnite statistics")
async def fortnite(ctx, username):
	r = fortnite_br_stats(username)
	if r.json()['status'] == 403:
		await ctx.respond("`" + username + "`" + " set their stats to private")
		return
	if r.json()['status'] != 200:
		await ctx.respond("`" + username + "`" " doesn't exist or hasn't played any games yet")
		return
	data = r.json()['data']
	name = data['account']['name']
	level = data['battlePass']['level']
	embed = discord.Embed(title="All time statistics for " + name)
	stats = data['stats']['all']['overall']
	fields = [
		("Wins", "wins", lambda x: x),
		("Top 3", "top3", lambda x: x),
		("Top 5", "top5", lambda x: x),
		("Top 6", "top6", lambda x: x),
		("Top 10", "top10", lambda x: x),
		("Top 12", "top12", lambda x: x),
		("Top 25", "top25", lambda x: x),
		("Kills", "kills", lambda x: x),
		("Kills per minute", "killsPerMin", lambda x: x),
		("Kills per match", "killsPerMatch", lambda x: x),
		("Deaths", "deaths", lambda x: x),
		("K/D", "kd", lambda x: x),
		("Matches", "matches", lambda x: x),
		("Winrate", "winRate", lambda x: x),
		("Minutes played", "minutesPlayed", lambda x: f"{x} minutes ({x / (24 * 60):.2f} days)"),
		("Players outlived", "playersOutlived", lambda x: x),
		("Last modified", "lastModified", lambda x: x),
	]
	embed.add_field(name="Level (current season)", value=level, inline=False)
	for field in fields:
		name, key, func = field
		value = func(stats.get(key))
		embed.add_field(name=name, value=value, inline=False)

	await ctx.respond(embed=embed)

@discordClient.slash_command(description="View the current Battle Royale map")
async def fortnite_map(ctx):
	await ctx.defer()
	url = "https://media.fortniteapi.io/images/map.png?showPOI=true"
	r = requests.get(url, stream = True)
	if r.status_code == 200:
		newuuid = str(uuid.uuid4())
		with open(newuuid + ".png", "wb") as f:
			shutil.copyfileobj(r.raw, f)
			await asyncio.sleep(2)
			await ctx.edit(file=discord.File(newuuid + ".png"))
			if os.path.exists(newuuid + ".png"):
				os.remove(newuuid + ".png")
	else:
		await ctx.respond("A " + str(r.status_code) + " happened")

@discordClient.slash_command(description="[Owner] Query the database with an SQL command")
async def sql_fetchall(ctx, query):
	print(ctx.user.id)
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		try:
			q = cursor.execute(query).fetchall()
			await ctx.respond(q)
		except Exception as e:
			await ctx.respond("Not a valid query. Reason: " + str(repr(e)))

@discordClient.slash_command(description="[Owner] Query the database with an SQL command")
async def sql(ctx, query):
	print(ctx.user.id)
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		try:
			cursor.execute(query)
			await ctx.respond("Executed ✅")
		except Exception as e:
			await ctx.respond("Not a valid query. Reason: " + str(repr(e)))

@discordClient.slash_command(description="Check the bot's ping")
async def ping(ctx):
	await ctx.respond("Ponged your ping in " + str(round(discordClient.latency * 1000)) + "ms 😳")

@discordClient.slash_command(description="Get a user's Epic Games ID")
async def fortnite_get_id(ctx, username):
	await ctx.respond(getAccountID(username))

@discordClient.slash_command()
async def delete_message_by_id(ctx, id):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
		return
	try:
		channel = ctx.channel
		message = await channel.fetch_message(id)
		await message.delete()
		await ctx.respond("Deleted", ephemeral=True)
	except Exception as e:
		await ctx.respond(e)

@discordClient.slash_command(description="[Owner] SIGKILL the bot's PID")
async def die(ctx):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
		return
	await ctx.respond("Death request received 🫡")
	os.kill(int(os.getpid()), signal.SIGKILL)
	await discordClient.close()

lego = discordClient.create_group("lego")

@lego.command(description="Search a Lego item")
async def search(ctx, string):
	product_url = 'https://www.lego.com/en-au/product/'
	products = search_lego_item(string)
	if products:
		pages = []
		num_results = products['total']
		results = products['results']
		for item in results:
			embed = discord.Embed(
				title=item['name'],
				url=product_url + item['slug']
			)
			embed.set_image(url=item['baseImgUrl'])
			embed.add_field(name="Price", value=item['variant']['price']['formattedAmount'], inline=True)
			embed.add_field(name="Availability", value=item['variant']['attributes']['availabilityText'])
			embed.set_footer(text=f"Returned {num_results} results")
			pages.append(Page(content=item['name'], embeds=[embed]))
		paginator = Paginator(pages=pages)
		await paginator.respond(ctx.interaction)
	else:
		await ctx.respond("Something went wrong. Please try again.")

@lego.command(description="Add or remove an item")
async def edit(ctx, id):
	await ctx.defer()
	result = get_lego_item_by_id(id)
	result = result['data']['product']
	if result:
		name = result['name']
		image_url = result['baseImgUrl']
		slug = result['slug']
		availability = result['variant']['attributes']['availabilityText']
		on_sale = result['variant']['attributes']['onSale']
		price = result['variant']['price']['formattedAmount']
		result_db = cursor.execute("SELECT * FROM lego WHERE id = ?", (id,)).fetchone()
		if result_db:
			cursor.execute("DELETE FROM lego WHERE id = ?", (id,)).fetchone()
			await ctx.respond(f"Removed {name} from your list")
		else:
			cursor.execute("INSERT INTO lego VALUES (?, ?, ?, ?, ?, ?, ?)", (id, name, image_url, slug, availability, on_sale, price))
			await ctx.respond(f"Added {name} to your list")
	else:
		await ctx.respond(f"{id} didn't return any results :(")

@lego.command(description="View your tracked items")
async def list(ctx):
	tracked = cursor.execute("SELECT * FROM lego")
	embed = discord.Embed(title = "Items you're tracking")
	for item in tracked:
		id = item[0]
		name = item[1]
		availability = item[4]
		on_sale = item[5]
		price = item[6]
		compact_info = f"**Name**: {name}\n**Price**: {price}\n**On special**: {'Yes' if on_sale else 'No'}\n**Availability**: {availability}"
		embed.add_field(name=f"{id} - {name}", value=compact_info, inline=False)
	await ctx.respond(embed=embed)

@discordClient.slash_command(description="Generate an image with DALL-E 3")
async def dalle3(ctx, prompt):
	await ctx.defer()
	await ctx.respond(dalle_prompt(prompt))

# @discordClient.event
# async def on_message(message):
# 	if message.author == discordClient.user and message.reference:
# 		message_author = "assistant"
# 		print("Message is a reply from bot to user, so it should be added to the thread.")
# 	elif message.author == discordClient.user and not message.reference:
# 		return
# 	else:
# 		message_author = "user"
# 	if message.attachments:
# 		for attachment in message.attachments:
# 			attachment_type, attch_format = attachment.content_type.split('/')
# 			if attachment_type == 'image':
# 				add_to_thread(message_author, [
# 										{"type": "text", "text": message.author.display_name + ": " + message.content if message.author != discordClient.user else message.content},
# 										{"type": "image_url", "image_url": {"url": attachment.url, "detail": "high"}}
# 									])
# 			if attachment_type == 'video':
# 				if attachment.size > 52428800:
# 					await message.add_reaction("❌")
# 					return
# 				channel = discordClient.get_channel(int(os.getenv('CLIPS_CHANNEL')))
# 				button = Button(label="Jump", style=discord.ButtonStyle.link, url=message.jump_url)
# 				view = View()
# 				view.add_item(button)
# 				await channel.send(attachment.url, view=view)
# 				await message.add_reaction("✅")
# 	elif message.embeds:
# 		for embed in message.embeds:
# 			try:
# 				add_to_thread(message_author, [
# 											{"type": "text", "text": message.author.display_name + ": " + message.content if message.author != discordClient.user else message.content},
# 											{"type": "image_url", "image_url": {"url": embed.thumbnail.url, "detail": "high"}}
# 										])
# 			except:
# 				try:
# 					add_to_thread(message_author, message.content)
# 				except:
# 					pass #no message content
# 	else:
# 		add_to_thread(message_author, message.content)
# 	if discordClient.user in message.mentions or str(message.channel.type) == 'private':
# 		async with message.channel.typing():
# 			await message.reply(create_run())
# 	if 'heh' in message.content.lower():
# 		emoji = discordClient.get_emoji(int(os.getenv('HEH_EMOJI')))
# 		await message.add_reaction(emoji)
# 	if 'perhaps' in message.content.lower():
# 		await message.add_reaction("🦀")
# 	if '@everyone' in message.content.lower() and not message.channel.permissions_for(message.author).mention_everyone:
# 		await message.channel.send(file=discord.File("assets/everyone.gif"))

@discordClient.event
async def on_message(message):
	if message.author == discordClient.user:
		return
	if embed_tweets(message):
		webhook = (await message.channel.webhooks())[0]
		await webhook.send(content=embed_tweets(message), username=message.author.name, avatar_url=message.author.avatar)
		await message.delete()
		return
	if discordClient.user in message.mentions or str(message.channel.type) == 'private':
		async with message.channel.typing():
			contents = []
			initial_message = {"role": "system", "content": "You're a helpful and decisive lad that LOVES Fortnite and answers any questions. Even if the questions aren't fortnite-related, you manage to sneak a Fortnite reference into each answer."}
			contents.append(initial_message)
			if message.reference:
				referenced = await message.channel.fetch_message(message.reference.message_id)
				messages = [message, referenced]
			else:
				messages = await message.channel.history(limit=10).flatten()
			messages.reverse()
			for msg in messages:
				if msg.embeds:
					for embed in msg.embeds:
						try:
							contents.append({
									"role": "user" if msg.author != discordClient.user else "assistant",
									"content": [
										{"type": "text", "text": msg.author.display_name + ": " + msg.content if msg.author != discordClient.user else msg.content},
										{"type": "image_url", "image_url": {"url": embed.thumbnail.url, "detail": "high"}}
									]
								})
						except:
							pass #probably no thumbnail url :/
				elif message.attachments:
					for attachment in msg.attachments:
						attachment_type, attch_format = attachment.content_type.split('/')
						if attachment_type == 'image':
							contents.append({
								"role": "user" if msg.author != discordClient.user else "assistant",
								"content": [
									{"type": "text", "text": msg.author.display_name + ": " + msg.content if msg.author != discordClient.user else msg.content},
									{"type": "image_url", "image_url": {"url": attachment.url, "detail": "high"}}
								]
							})
				else:
					contents.append({"role": "user" if msg.author != discordClient.user else "assistant", "content": msg.author.display_name + ": " + msg.content if msg.author != discordClient.user else msg.content})
			await message.reply(openai_chat(contents), mention_author=False)	
	for attachment in message.attachments:
		attachment_type, attch_format = attachment.content_type.split('/')
		if attachment_type == 'video':
			if attachment.size > 52428800:
				link_message = attachment.url + "Media is too large to embed - please jump to the original message"
			else:
				link_message = attachment.url
			channel = discordClient.get_channel(int(os.getenv('CLIPS_CHANNEL')))
			button = Button(label="Jump", style=discord.ButtonStyle.link, url=message.jump_url)
			view = View()
			view.add_item(button)
			await channel.send(link_message, view=view)
			await message.add_reaction("✅")
		if attachment_type == 'audio':
			await attachment.save("audio.mp3")
			response = transcribe_audio("audio.mp3")
			await message.channel.send(response.text)
	if 'heh' in message.content.lower():
		emoji = discordClient.get_emoji(int(os.getenv('HEH_EMOJI')))
		await message.add_reaction(emoji)
	if 'perhaps' in message.content.lower():
		await message.add_reaction("🦀")
	if '@everyone' in message.content.lower() and not message.channel.permissions_for(message.author).mention_everyone:
		await message.channel.send(file=discord.File("assets/everyone.gif"))

@discordClient.event
async def on_voice_state_update(member, before, after):
    if member == discordClient.user:
        return
    if before.channel is None and after.channel is not None:
        print(f"{member} joined {after.channel.id}")
        users = cursor.execute("SELECT * from pingme").fetchall()
        users_id = [user[0] for user in users]
        if member.id in users_id:
            return
        else:
            for user_id in users_id:
                await after.channel.send(f"<@{user_id}>, {member} just joined.")

@discordClient.event
async def on_reaction_add(reaction, user):
	if user == discordClient.user:
		return
	if reaction.emoji == "👀" and user != discordClient.user:
		users = await reaction.users().flatten()
		if discordClient.user in users:
			await reaction.clear()
			id = reaction.message.id
			response = cursor.execute("SELECT guess, score FROM ai WHERE id = ?", (id,)).fetchall()
			await reaction.message.reply(str(response) + "\nRequested by " + user.mention, mention_author=False)
	if reaction.emoji == "💡" and user != discordClient.user:
		users = await reaction.users().flatten()
		if discordClient.user in users:
			await reaction.clear()
			id = reaction.message.id
			response = cursor.execute("SELECT guess, score FROM ai_text WHERE id = ?", (id,)).fetchall()
			await reaction.message.reply(str(response) + "\nRequested by " + user.mention, mention_author=False)

@discordClient.event
async def on_member_update(before, after):
    if before == discordClient.user or not after.nick:
        return

@discordClient.event
async def on_member_remove(member):
	channel = discordClient.get_channel(int(os.getenv('BEG_4_VBUCKS')))
	await channel.send(f"{member} just left the server. https://tenor.com/view/thanos-fortnite-takethel-dance-gif-12100688")

def send_stdout_to_discord(message):
	message = message.strip()
	if message:
		channel = discordClient.get_channel(int(os.getenv('STDOUT')))
		if channel:
			asyncio.ensure_future(channel.send(message))

def send_stdout_to_discord(message):
    message = message.strip()

    if message:
        channel = discordClient.get_channel(int(os.getenv('STDOUT')))
        
        if channel:
            if len(message) > 2000:
                chunks = [message[i:i+2000] for i in range(0, len(message), 2000)]
                
                for chunk in chunks:
                    asyncio.ensure_future(channel.send(chunk))
            else:
                asyncio.ensure_future(channel.send(message))

sys.stdout.write = send_stdout_to_discord
sys.stderr.write = send_stdout_to_discord

discordClient.run(os.getenv('TOKEN'))