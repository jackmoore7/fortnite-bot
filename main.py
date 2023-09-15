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
from discord.ext import commands, pages
from discord.ext.pages import Paginator, Page
from discord.ui import Button, View
from discord import Option
import sqlite3 as sl
from dotenv import load_dotenv
import glob
import urllib.request
from num2words import num2words
import imghdr
import faulthandler, signal
from PIL import Image
import json
import traceback

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

intents = discord.Intents.all()
intents.members = True

discordClient = discord.Bot(intents=intents)

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

tasks_list = {}

aldi_regex = r'(?i)[a4@]\s*[il1\|]\s*d\s*[il1\|]'

@discordClient.event
async def on_ready():
	await discordClient.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for <store>"))
	fortnite_update_bg.start()
	tv_show_update_bg.start()
	fortnite_status_bg.start()
	fortnite_shop_update_v2.start()
	fortnite_shop_offers.start()
	coles_specials_bg.start()
	arpansa.start()
	epic_free_games.start()
	tasks_list["update"] = fortnite_update_bg
	tasks_list["tv"] = tv_show_update_bg
	tasks_list["status"] = fortnite_status_bg
	tasks_list["shop"] = fortnite_shop_update_v2
	tasks_list["offers"] = fortnite_shop_offers
	tasks_list["coles"] = coles_specials_bg
	tasks_list["arpansa"] = arpansa
	print(f"{discordClient.user} is online! My PID is {os.getpid()}.")

@tasks.loop(minutes=1)
async def fortnite_update_bg():
	try:
		channel = discordClient.get_channel(int(os.getenv('UPD8_CHANNEL')))
		response = get_fortnite_update_manifest()
		current_version = cursor.execute("SELECT version FROM aes").fetchone()[0]
		if current_version != response:
			cursor.execute("UPDATE aes SET version = ?", (response,))
			embed = discord.Embed(title="A new Fortnite update was just deployed")
			embed.set_footer(text="Use /update to subscribe to notifications")
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
			print("No recent episode entries. Skipping...")
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
		user = discordClient.get_user(int(os.getenv('ME')))
		items = cursor.execute("SELECT * FROM coles_specials").fetchall()
		for product in items:
			special_status = get_item_by_id(product[0])
			if isinstance(special_status, tuple):
				if product[6] != special_status[6]:
					if special_status[6]:
						await user.send(f"{product[2]} {product[1]} is now available for purchase.")
					else:
						await user.send(f"{product[2]} {product[1]} is no longer available for purchase.")
					cursor.execute("UPDATE coles_specials SET available = ? WHERE id = ?", (special_status[6], product[0]))
				if product[5] != special_status[5]:
					if special_status[5]:
						cursor.execute("UPDATE coles_specials SET on_sale = ? WHERE id = ?", (special_status[5], product[0]))
						await user.send(f"{product[2]} {product[1]} is on sale for ${special_status[4]}!")
					else:
						cursor.execute("UPDATE coles_specials SET on_sale = ? WHERE id = ?", (special_status[5], product[0]))
						await user.send(f"{product[2]} {product[1]} is no longer on sale and back to its usual price of ${special_status[4]}")
				if (product[4] != special_status[4]):
					cursor.execute("UPDATE coles_specials SET current_price = ? WHERE id = ?", (special_status[4], product[0]))
					if product[4] > special_status[4]:
						await user.send(f"The price of {product[2]} {product[1]} was reduced from ${product[4]} to ${special_status[4]}")
					else:
						await user.send(f"The price of {product[2]} {product[1]} was increased from ${product[4]} to ${special_status[4]}")
			else:
				if special_status == "nah":
					await user.send(f"{product[2]} {product[1]} returned a 404. It may no longer be available.")
	except Exception as e:
		await user.send("Something went wrong getting item details from Coles: " + str(repr(e)) + "\nRestarting internal task in 3 hours")
		await asyncio.sleep(10800)
		coles_specials_bg.restart()

@tasks.loop(minutes=3)
async def fortnite_status_bg():
	try:
		channel = discordClient.get_channel(int(os.getenv('UPD8_CHANNEL')))
		response = get_fortnite_status()
		current_status = cursor.execute("SELECT * FROM server").fetchall()[0][0]
		if current_status != response:
			cursor.execute("UPDATE server SET status = ?", (response,))
			embed = discord.Embed(title = "Fortnite server status update")
			embed.set_footer(text="Use /update to subscribe to notifications")
			embed.add_field(name="Status", value=response)
			await channel.send("<@&" + os.getenv('UPD8_ROLE') + ">", embed=embed)
	except Exception as e:
		print("Something went wrong getting the Fortnite status: " + str(repr(e)) + "\nRestarting internal task in 3 minutes.")
		await asyncio.sleep(180)
		fortnite_status_bg.restart()

@tasks.loop(minutes=5)
async def fortnite_shop_update_v2():
	try:
		channel = discordClient.get_channel(int(os.getenv('SHOP_CHANNEL')))
		r = fortnite_shop()
		uid = cursor.execute("SELECT uid FROM shop").fetchone()[0]
		new_uid = r['lastUpdate']['uid']
		no_images = []
		if new_uid != uid:
			# today = [(item['displayAssets'][0]['full_background'], item['displayName']) for item in r['shop']]
			today = []
			for item in r['shop']:
				if 'displayAssets' in item and item['displayAssets'] and 'full_background' in item['displayAssets'][0]:
					today.append((item['displayAssets'][0]['full_background'], item['displayName']))
				else:
					no_images.append(item['displayName'])

			yesterday = cursor.execute("SELECT * FROM shop_content").fetchall()
			diff = [tup for tup in today if tup[1] not in (y[1] for y in yesterday)]
			if len(diff) < 1:
				print("The shop was just updated, but there are no new items.")
				diff2 = [tup for tup in yesterday if tup[1] not in (t[1] for t in today)] #check if something was deleted from the list
				if len(diff2) > 0:
					await channel.send("The following items were just deleted from the shop:")
					for item in diff2:
						await channel.send(f"{item[1]}")
				cursor.execute("UPDATE shop SET uid = ?", (new_uid,))
				return
			for item in diff:
				if item[0]:
					newuuid = str(uuid.uuid4())
					img = urllib.request.urlopen(item[0])
					img_data = img.read()
					img_type = imghdr.what(None, h=img_data)
					if img_type:
						max_retries = 5
						for attempt in range(max_retries):
							try:
								with open(f'temp_images/{newuuid}.{img_type}', "wb") as f:
									f.write(img_data)
								image = Image.open(f'temp_images/{newuuid}.{img_type}')
								image.verify()
								print(f"{newuuid} was successfully downloaded and verified")
								break
							except Exception as e:
								print(f"Broken image detected: {e}")
								os.remove(f'temp_images/{newuuid}.{img_type}')
								if attempt < max_retries - 1:
									print(f"Retrying ({attempt + 1}/{max_retries})...")
									await asyncio.sleep(2)
								else:
									print(f"Max retries reached, failed to download {newuuid}")
									no_images.append(item[1])
									break
					else:
						no_images.append(item[1])
				else:
					no_images.append(item[1])
			print("Finished downloading shop images")
			if len(diff) == 1:
				await channel.send("1 item was just added to the shop.")
			else:	
				await channel.send(f"{len(diff)} items were just added to the shop.")
			item_list = cursor.execute("SELECT item, id FROM shop_ping").fetchall()
			for item in diff:
				matching_items = [i for i, u in item_list if i.lower() in item[1].lower()]
				for cosmetic in matching_items:
					users = [u for i, u in item_list if i == cosmetic]
					for user in users:
						await channel.send(f"<@{user}>, {item[1]} is in the shop\nTriggered by your keyword: {cosmetic}")
			files = glob.glob('temp_images/*.png')
			for f in files:
				await channel.send(file=discord.File(f))
				os.remove(f)
			if no_images:
				await channel.send("The following items did not have associated images or failed to download after multiple attempts:")
				for item in no_images:
					await channel.send(item)
			await channel.send("---")
			cursor.execute("DELETE FROM shop_content")
			cursor.executemany("INSERT INTO shop_content VALUES (?, ?)", [(item[0], item[1]) for item in today])
			cursor.execute("UPDATE shop SET uid = ?", (new_uid,))
	except Exception as e:
		print(traceback.format_exc())
		files = glob.glob('temp_images/*.png')
		for f in files:
			os.remove(f)
		await asyncio.sleep(60)
		fortnite_shop_update_v2.restart()

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

	def timestampify(string):
		date_time_obj = dt.strptime(string, '%Y-%m-%dT%H:%M:%S.%fZ')
		struct_time = date_time_obj.timetuple()
		return f"<t:{int(mktime(struct_time))}:R>"
		

	channel = discordClient.get_channel(int(os.getenv('SHOP_CHANNEL')))
	r = fortnite_shop_v3()
	date = cursor.execute("SELECT date FROM shop_v3").fetchone()[0]
	new_date = r['data']['date']
	if new_date != date:
		ping_list = cursor.execute("SELECT item, id FROM shop_ping").fetchall()
		no_images = []
		daily = []
		for item in r['data']['daily']:
			if 'gallery' in item['images'] and item['images']['gallery']:
				daily.append((item['images']['gallery'], item['name'], item['history']['lastSeen']))
			elif 'featured' in item['images'] and item['images']['featured']:
				daily.append((item['images']['featured'], item['name'], item['history']['lastSeen']))
			elif 'icon' in item['images'] and item['images']['icon']:
				daily.append((item['images']['icon'], item['name'], item['history']['lastSeen']))
			else:
				no_images.append((item['name'], item['history']['lastSeen']))
		featured = []
		for item in r['data']['featured']:
			if 'gallery' in item['images'] and item['images']['gallery']:
				featured.append((item['images']['gallery'], item['name'], item['history']['lastSeen']))
			elif 'featured' in item['images'] and item['images']['featured']:
				featured.append((item['images']['featured'], item['name'], item['history']['lastSeen']))
			elif 'icon' in item['images'] and item['images']['icon']:
				featured.append((item['images']['icon'], item['name'], item['history']['lastSeen']))
			else:
				no_images.append((item['name'], item['history']['lastSeen']))
		yesterday = cursor.execute("SELECT * FROM shop_v3_content").fetchall()
		diff = [item for item in featured if item[1] not in (item[1] for item in yesterday)]
		if len(diff) < 1:
			diff2 = [item for item in yesterday if item[1] not in (item[1] for item in featured)] #check if something was deleted from the list
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
		await channel.send("## Daily rotation")
		for item in daily:
			img = process_image(item[0], item[1])
			matching_items = [i for i, u in ping_list if i.lower() in item[1].lower()]
			for cosmetic in matching_items:
				users = [u for i, u in ping_list if i == cosmetic]
				for user in users:
					await channel.send(f"<@{user}>, {item[1]} is in the shop\nTriggered by your keyword: {cosmetic}")
			await channel.send(f"{item[1]} - Last seen {timestampify(item[2])}", file=discord.File(f'temp_images/{img}'))
			os.remove(f'temp_images/{img}')
		await channel.send("## Featured")
		for item in diff:
			img = process_image(item[0], item[1])
			matching_items = [i for i, u in ping_list if i.lower() in item[1].lower()]
			for cosmetic in matching_items:
				users = [u for i, u in ping_list if i == cosmetic]
				for user in users:
					await channel.send(f"<@{user}>, {item[1]} is in the shop\nTriggered by your keyword: {cosmetic}")
			await channel.send(f"{item[1]} - Last seen {timestampify(item[2])}", file=discord.File(f'temp_images/{img}'))
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

	def timestampify(string):
		date_time_obj = dt.strptime(string, '%Y-%m-%dT%H:%M:%S.%fZ')
		struct_time = date_time_obj.timetuple()
		timestamp = f"<t:{int(mktime(struct_time))}:R>"
		return timestamp

	def test_time(string):
		start_dt = dt.fromisoformat(string[:-1])
		current_dt = dt.utcnow()
		if current_dt >= start_dt:
			return True
		else:
			return False

	games_list = get_free_games()
	existing_games_list = cursor.execute("SELECT * FROM free_games").fetchall()
	for game in existing_games_list:
		if test_time(game[3]):
			await ch.send(f"<@&{os.getenv('FREE_GAMES_ROLE')}>, {game[0]} is available to claim right now!")
			cursor.execute("DELETE FROM free_games WHERE title = ?", (game[0],))
	diff = [game for game in games_list if game[0] not in (game[0] for game in existing_games_list)]
	if len(diff) > 0:
		for game in diff:
			if test_time(game[3]):
				pass
			embed = discord.Embed()
			embed.title = "New free game on the Epic Games store"
			embed.set_image(url=game[2])
			embed.add_field(name="Title", value=game[0], inline=False)
			embed.add_field(name="Description", value=game[1], inline=False)
			embed.add_field(name="Starts", value=timestampify(game[3]))
			embed.add_field(name="Ends", value=timestampify(game[4]))
			await ch.send(embed=embed)
			cursor.execute("INSERT INTO free_games VALUES (?, ?, ?, ?)", (game[0], game[1], game[2], game[3]))
	else:
		diff2 = [game for game in existing_games_list if game[1] not in (game[1] for game in games_list)]
		if len(diff2) > 0:
			for game in diff2:
				print(f"Promotional period ended for {game[0]}")
				cursor.execute("DELETE FROM free_games WHERE title = ?", (game[0],))

@tasks.loop(minutes=60)
async def fortnite_shop_offers():
	try:
		today_offers = get_fortnite_shop_offers()
		yesterday_offers = cursor.execute("SELECT * FROM shop_offers").fetchall()
		offer_diff = [tup for tup in today_offers if tup['title'] not in (y[1] for y in yesterday_offers)]
		if len(offer_diff) > 0:
			print(offer_diff)
			channel = discordClient.get_channel(int(os.getenv('SHOP_CHANNEL')))
			if len(offer_diff) == 1:
				await channel.send("There is 1 new offer in the shop")
			else:
				await channel.send(f"There are {len(offer_diff)} new offers in the shop")
			for item in offer_diff:
				if item['expiryDate']:
					date_time_obj = dt.strptime(item['expiryDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
					struct_time = date_time_obj.timetuple()
					timestamp = f"<t:{int(mktime(struct_time))}:R>"
				else:
					timestamp = "<t:2147483647:R>"
				og_price = item['price']['totalPrice']['fmtPrice']['originalPrice'][2:]
				discount_price = item['price']['totalPrice']['fmtPrice']['discountPrice'][2:]
				if og_price and discount_price:
					difference = float(og_price) - float(discount_price)
					if difference != 0:
						await channel.send(f"{item['title']}\n{item['price']['totalPrice']['fmtPrice']['discountPrice']} (${difference} off!)\nExpires {timestamp}\n{item['keyImages'][0]['url']}")
					else:
						await channel.send(f"{item['title']}\n{item['price']['totalPrice']['fmtPrice']['discountPrice']}\nExpires {timestamp}\n{item['keyImages'][0]['url']}")
				else:
					await channel.send(f"{item['title']}\nFree!\nExpires {timestamp}\n{item['keyImages'][0]['url']}")
		else:
			return
		cursor.execute("DELETE FROM shop_offers")
		for item in today_offers:
			cursor.execute("INSERT INTO shop_offers VALUES (?, ?, ?, ?, ?, ?)", (item['id'], item['title'], item['expiryDate'], item['keyImages'][0]['url'], item['price']['totalPrice']['fmtPrice']['originalPrice'], item['price']['totalPrice']['fmtPrice']['discountPrice']))
	except Exception as e:
		print(e)
		channel = discordClient.get_channel(int(os.getenv('SHOP_CHANNEL')))
		await channel.send("Something went HORRIBLY TERRIBLY wrong with the shop offers task. Restarting in 30 minutes.")
		await asyncio.sleep(1800)
		fortnite_shop_offers.restart()

start_time = time(20, 1, 0)
end_time = time(7, 0, 0)
time_list = [time(hour, minute) for hour in range(start_time.hour, 24) for minute in range(0, 60, 1)] + [time(hour, minute) for hour in range(end_time.hour + 1) for minute in range(0, 60, 1)]

@tasks.loop(time=time_list)
async def arpansa():
	try:
		ch = discordClient.get_channel(int(os.getenv('UV_CHANNEL')))
		role = os.getenv('SUNSCREEN_ROLE')
		current_date = dt.now(pytz.timezone('Australia/Sydney')).strftime('%Y-%m-%d')
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
				await ch.send(f"<@&{role}>")
				embed.add_field(name="Time", value=f"{first_forecast_gte_3_item['Date'][-5:]} - {first_forecast_lt_3_item['Date'][-5:]}", inline=False)
				cursor.execute("UPDATE uv_times SET safe = 0")
			else:
				embed.title = "No sun protection required today"
				cursor.execute("UPDATE uv_times SET safe = 1")
			embed.add_field(name="Maximum UV (Forecast)", value=f"{calculate_emoji(max_uv_today_forecast)} {max_uv_today_forecast} at {max_uv_today_forecast_time}", inline=False)
			embed.add_field(name="Maximum UV (Recorded)", value=f"{calculate_emoji(max_uv_today_recorded)} {max_uv_today_recorded} at {max_uv_today_recorded_time}", inline=False)
			embed.add_field(name="Current UV", value=f"{calculate_emoji(current_uv)} {current_uv}", inline=False)
			msg = await ch.send(embed=embed)
			cursor.execute("UPDATE uv_times SET end = ?", (msg.id,))
			cursor.execute("UPDATE uv_times SET start = ?", (current_date,))

		msg = await ch.fetch_message(int(cursor.execute("SELECT end FROM uv_times").fetchone()[0]))
		emb = msg.embeds[0]
		emb.set_field_at(-1, name="Current UV", value=f"{calculate_emoji(current_uv)} {current_uv}")
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

@discordClient.slash_command(description="Search a Coles item by name")
async def search_coles_item(ctx, name):
	await ctx.defer()
	try:
		result = search_item(name)
		if result[0] == 0:
			await ctx.respond("No results")
			return
		list_str = "```" + "\n".join([f"{i}. {item[1]} ({item[2]}) - ID: {item[0]}" for i, item in enumerate(result[1:], start=1)]) + "```"
		response = f"{list_str}"
		await ctx.respond(response)
	except discord.errors.HTTPException as e:
		if "Must be 2000 or fewer in length." in str(e):
			await ctx.respond(f"Your search returned {result[0]} results. Please make your search term more specific.")

coles_list = discordClient.create_group("coles_list", "Edit your tracked items list")

class MyView(discord.ui.View):

	def __init__(self, item_id):
		super().__init__()
		self.item_id = item_id

	@discord.ui.button(label="Yes, delete", row=0, style=discord.ButtonStyle.danger)
	async def first_button_callback(self, button, interaction):
		self.disable_all_items()
		try:
			cursor.execute("DELETE FROM coles_specials WHERE id = ?", (self.item_id,))
			button.label = "Item deleted"
		except Exception as e:
			button.label = f"Couldn't delete item: {e}"
		await interaction.response.edit_message(view=self)

	@discord.ui.button(label="No, keep", row=0, style=discord.ButtonStyle.primary)
	async def second_button_callback(self, button, interaction):
		self.disable_all_items()
		button.label = "Kept!"
		await interaction.response.edit_message(view=self)

@coles_list.command(description="Add or remove an item")
async def edit(ctx, id):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		result = add_item_to_db_by_id(id)
		if "already" in result:
			await ctx.respond(result, view=MyView(item_id=id))
		else:
			await ctx.respond(result)

@coles_list.command(description="View your tracked items")
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

@discordClient.slash_command(description="[Owner] Reboot the bot")
async def reboot(ctx):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
	else:
		try:
			await ctx.respond("✅")
			os.execl(sys.executable, sys.executable, *sys.argv)
		except Exception as e:
			await ctx.respond(e)

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

@discordClient.slash_command(description="Get pinged when someone joins a voice channel")
async def pingme(ctx):
	user_id = ctx.user.id
	user = cursor.execute("SELECT * FROM pingme WHERE user = ?", (user_id,)).fetchone()
	if user:
		cursor.execute("DELETE FROM pingme WHERE user = ?", (user_id,))
		await ctx.respond("Removed ✅")
	else:
		cursor.execute("INSERT INTO pingme VALUES (?)", (user_id,))
		await ctx.respond("Added ✅")

@discordClient.slash_command(description="Get pinged for sun protection forecasts")
async def sunscreen(ctx):
	role = ctx.guild.get_role(int(os.getenv('SUNSCREEN_ROLE')))
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
	if 'aldi' in item.lower():
		await ctx.respond("No")
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
	embed = discord.Embed(title = "All time statistics for " + name)
	stats = data['stats']['all']['overall']
	fields = [
		("Wins", "wins"),
		("Top 3", "top3"),
		("Top 5", "top5"),
		("Top 6", "top6"),
		("Top 10", "top10"),
		("Top 12", "top12"),
		("Top 25", "top25"),
		("Kills", "kills"),
		("Kills per minute", "killsPerMin"),
		("Kills per match", "killsPerMatch"),
		("Deaths", "deaths"),
		("K/D", "kd"),
		("Matches", "matches"),
		("Winrate", "winRate"),
		("Minutes played", "minutesPlayed"),
		("Players outlived", "playersOutlived"),
		("Last modified", "lastModified"),
	]
	embed.add_field(name="Level (current season)", value=level, inline=False)
	for field in fields:
		embed.add_field(name=field[0], value=stats.get(field[1]), inline=False)
	await ctx.respond(embed=embed)

@discordClient.slash_command(description="See the biggest fish a user caught this season")
async def fortnite_fish(ctx, username):
	await ctx.respond("Fish collection is not present in this season.")
	return
	await ctx.defer()
	new_record = False
	r = fish_stats(username)
	if r == "no":
		await ctx.respond("User not found")
		return
	if r == 404:
		await ctx.respond("Something went wrong")
		return
	r1 = fish_loot_pool()
	biggest = 0
	name = ""
	current_season_fish = False
	if len(r) < 1: #an empty list means a user's statistics have been set to private
		await ctx.respond("Statistics for `" + username + "` have been set to private.")
		return
	for i in r['stats']:
		if i['season'] == r1['season']: #looking for fish in the user's loot pool that are present in the current season
			r = i['fish']
			current_season_fish = True
	if current_season_fish == False:
		await ctx.respond("`" + username + "` hasn't caught any fish this season.")
		return
	for fish in r:
		if fish['length'] > biggest:
			biggest = fish['length']
			name = fish['name']
	rows = cursor.execute("SELECT fish_size FROM users WHERE username = ?", (username,),).fetchall()
	if len(rows) < 1: #no record for this user in the database yet
		cursor.execute("INSERT INTO users VALUES (?, ?, ?)", (username, name, biggest))
		rows = cursor.execute("SELECT fish_size FROM users WHERE username = ?", (username,),).fetchall()
	if(rows[0][0] < biggest): #API returned a bigger fish than what is present in the database
		cursor.execute(
			"UPDATE users SET fish_size = ?, fish_name = ? WHERE username = ?",
			(biggest, name, username)
		)
		new_record = True
	biggest_fish_loot = r1['fish']
	biggest_loot = 0
	for fish in biggest_fish_loot:
		if fish['sizeMax'] > biggest_loot:
			biggest_loot = fish['sizeMax'] #set the biggest fish currently obtainable this season
	winner = cursor.execute("SELECT username, fish_name, fish_size FROM users WHERE fish_size = (SELECT MAX(fish_size) FROM users)").fetchall() 
	embed = discord.Embed(title = "Biggest fish " + username + " caught in Season " + str(r1['season']))
	if new_record == True:
		embed.add_field(name="Name", value=name + "\n\nCongrats, it's a new personal best!", inline=True)
	else:
		embed.add_field(name="Name", value=name, inline=True)
	embed.add_field(name="Size", value=str(biggest) + "cm", inline=True)
	embed.add_field(name="Current record", value="The current record for biggest fish is a " + "**" + str(winner[0][2]) + "cm** " + "**" + winner[0][1] + "**" + " caught by " + "**" + winner[0][0] + "**!" + "\nThe largest obtainable fish this season is **" + str(biggest_loot) + "cm**.", inline=False)
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

@discordClient.slash_command(description="[Owner] Whitelist a character")
async def whitelist(ctx, hex):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
		return
	try:
		cursor.execute("INSERT INTO whitelist VALUES(?)", (hex,))
		await ctx.respond("Added ✅")
	except:
		await ctx.respond("Not a valid query")
		return

@discordClient.slash_command(description="[Owner] Blacklist a character")
async def blacklist(ctx, hex):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
		return
	try:
		cursor.execute("INSERT INTO blacklist VALUES(?)", (hex,))
		await ctx.respond("Added ✅")
	except:
		await ctx.respond("Not a valid query")
		return

@discordClient.slash_command()
async def hexify(ctx, string):
	hex_string = "".join([character.encode("utf-8").hex() for character in string])
	await ctx.respond(hex_string, ephemeral=True)

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

@discordClient.slash_command()
async def elevation(ctx, lat, long):
	await ctx.respond(get_elevation(lat, long))

@discordClient.slash_command()
async def die(ctx):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
		return
	await ctx.respond("Death request received 🫡")
	await discordClient.close()

# @discordClient.slash_command(description="Ask ChatGPT a question (GPT-3.5-turbo, conversational)")
# async def chatgpt(ctx, message):
# 	await ctx.defer()
# 	try:
# 		# id = ctx.user.id
# 		id = 0
# 		messages_row = cursor.execute("SELECT messages FROM chatgpt WHERE id = ?", (id,)).fetchone()
# 		if messages_row:
# 			messages_list = json.loads(messages_row[0])
# 		else:
# 			messages_list = []
# 			initial_message = {"role": "system", "content": "you're a helpful and decisive lad that LOVES fortnite and answers any questions. even if the questions aren't fortnite-related, you manage to sneak a fortnite reference into each answer. you are also very biased towards fortnite and have a fortnite accent"}
# 			messages_list.append(initial_message)
# 		#messages_list = json.loads(messages_list)
# 		new_message = {"role": "user", "content": message}
# 		messages_list.append(new_message)
# 		response = chatgpt_query(messages_list)
# 		messages_list.append(response.choices[0].message)
# 		updated_messages_list = json.dumps(messages_list)
# 		cursor.execute("INSERT INTO chatgpt VALUES (?, ?)", (id, updated_messages_list))
# 		total_tokens = response.usage.total_tokens
# 		cost = (total_tokens/1000) * 0.00175
# 		msg = await ctx.respond(response.choices[0].message.content)
# 		cursor.execute("INSERT INTO chatgpt_cost VALUES (?, ?)", (msg.id, cost))
# 	except Exception as e:
# 		await ctx.respond(e)

chatgpt = discordClient.create_group("chatgpt", "Edit heh's AI settings")

class chatgptview(discord.ui.View):

	def __init__(self, prompt, user_id):
		self.prompt = prompt
		self.user_id = user_id
		super().__init__()

	@discord.ui.button(label="Yes, change", row=0, style=discord.ButtonStyle.primary)
	async def first_button_callback(self, button, interaction):
		if interaction.user.id == self.user_id:
			self.disable_all_items()
			try:
				cursor.execute("UPDATE chatgpt_prompt SET prompt = ?", (self.prompt,))
				cursor.execute("DELETE FROM chatgpt WHERE id = 0")
				button.label = "Role changed"
			except Exception as e:
				button.label = f"Couldn't edit role: {e}"
			await interaction.response.edit_message(view=self)
		else:
			await interaction.response.send_message("This button isn't yours!", ephemeral=True)
			return

	@discord.ui.button(label="No, keep", row=0, style=discord.ButtonStyle.danger)
	async def second_button_callback(self, button, interaction):
		if interaction.user.id != self.user_id:
			return

		self.disable_all_items()
		button.label = "Kept!"
		await interaction.response.edit_message(view=self)



@chatgpt.command(description="Ask ChatGPT a question (custom role, non-conversational)")
async def custom(
		ctx: discord.ApplicationContext,
		role: Option(str, "Enter the role you'd like ChatGPT to assume. Eg: \"You are a helpful assistant\"", required=True),
		message: Option(str, "The question you'd like to ask.", required=True)
		):
	await ctx.defer()
	try:
		messages_list = []
		initial_message = {"role": "system", "content": role}
		new_message = {"role": "user", "content": message}
		messages_list.append(initial_message)
		messages_list.append(new_message)
		response = chatgpt_query(messages_list)
		total_tokens = response.usage.total_tokens
		cost = (total_tokens/1000) * 0.00175
		msg = await ctx.respond(response.choices[0].message.content)
		cursor.execute("INSERT INTO chatgpt_cost VALUES (?, ?)", (msg.id, cost))
	except Exception as e:
		await ctx.respond(e)

@chatgpt.command(description="Delete conversation history")
async def delete_history(ctx):
	try:
		# id = ctx.user.id
		id = 0
		cursor.execute("DELETE FROM chatgpt WHERE id = ?", (id,))
		emoji = discordClient.get_emoji(int(os.getenv('ROO_EMOJI')))
		await ctx.respond(emoji)
	except Exception as e:
		await ctx.respond(e)

@chatgpt.command(description="Set heh's initial prompt (This will delete conversation history!)")
async def set_prompt(
		ctx: discord.ApplicationContext,
		role: Option(str, "Enter the role you'd like heh to assume. Eg: \"You are a helpful assistant\"", required=True)
		):
	try:
		user_id = ctx.user.id
		prompt = cursor.execute("SELECT prompt FROM chatgpt_prompt").fetchone()[0]
		await ctx.respond(f"Current role is:\n{prompt}\n\nAre you sure you want to change it to:\n{role}", view=chatgptview(prompt=role, user_id=user_id))
	except Exception as e:
		await ctx.respond(f"oopsie woopsie fucky wucky {e}")
		

# @discordClient.slash_command(description="Generate an image with DALL·E")
# async def dalle(ctx, prompt):
# 	await ctx.defer()
# 	try:
# 		image_url = dalle_prompt(prompt)
# 		newuuid = str(uuid.uuid4())
# 		img = urllib.request.urlopen(image_url)
# 		img_data = img.read()
# 		with open(f'dalle/{newuuid}.png', "wb") as f:
# 			f.write(img_data)
# 		msg = await ctx.respond(file=discord.File(f'dalle/{newuuid}.png'))
# 		os.remove(f'dalle/{newuuid}.png')
# 		cost = 0.02
# 		cursor.execute("INSERT INTO chatgpt_cost VALUES (?, ?)", (msg.id, cost))
# 	except Exception as e:
# 		await ctx.respond(e)

# @discordClient.slash_command(description="Generate a variation of an image you provide with DALL·E")
# async def dalle_variation(ctx):
# 	await ctx.defer()
# 	try:
# 		if ctx.message.reference and ctx.message.reference.cached_message:
# 			replied_message = ctx.message.reference.cached_message
# 			if replied_message.attachments:
# 				attachment = replied_message.attachments[0]
# 				newuuid = str(uuid.uuid4())
# 				await attachment.save(f'{newuuid}.png')
# 				image_url = dalle_image_variation(newuuid)
# 				os.remove(f'{newuuid}.png')
# 				newuuid = str(uuid.uuid4())
# 				img = urllib.request.urlopen(image_url)
# 				img_data = img.read()
# 				with open(f'dalle/{newuuid}.png', "wb") as f:
# 					f.write(img_data)
# 				msg = await ctx.respond(file=discord.File(f'dalle/{newuuid}.png'))
# 				os.remove(f'dalle/{newuuid}.png')
# 				cost = 0.02
# 				cursor.execute("INSERT INTO chatgpt_cost VALUES (?, ?)", (msg.id, cost))
# 			else:
# 				await ctx.respond("This message doesn't contain any attachments.")
# 		else:
# 			if ctx.message.reference:
# 				await ctx.respond("I don't have that message cached, maybe send it again!")
# 			await ctx.respond("You need to use this command with a reply to a message.")


		# message = await ctx.channel.fetch_message(message_id)
		# if len(message.attachments) > 0:
		# 	attachment = message.attachments[0]
		# 	newuuid = str(uuid.uuid4())
		# 	await attachment.save(f'{newuuid}.png')
		# 	image_url = dalle_image_variation(newuuid)
		# 	os.remove(f'{newuuid}.png')
		# 	newuuid = str(uuid.uuid4())
		# 	img = urllib.request.urlopen(image_url)
		# 	img_data = img.read()
		# 	with open(f'dalle/{newuuid}.png', "wb") as f:
		# 		f.write(img_data)
		# 	msg = await ctx.respond(file=discord.File(f'dalle/{newuuid}.png'))
		# 	os.remove(f'dalle/{newuuid}.png')
		# 	cost = 0.02
		# 	cursor.execute("INSERT INTO chatgpt_cost VALUES (?, ?)", (msg.id, cost))
		# else:
		# 	await ctx.respond("This message doesn't contain any images.")
	# except Exception as e:
	# 	await ctx.respond(e)

		
		

def time_to_text(hour:int, minute:int):
	if minute == 0:
		return num2words(hour) + " o'clock"
	elif minute == 15:
		return "quarter past " + num2words(hour)
	elif minute == 30:
		return "half past " + num2words(hour)
	elif minute == 45:
		return "quarter to " + num2words(hour)
	elif minute < 30:
		return num2words(minute) + " past " + num2words(hour)
	else:
		return num2words(60 - minute) + " to " + num2words(hour+1)

def get_24_hour_time(hour:int, hour_sent:int):
	hour_sent = (hour_sent + 9) % 24 #convert gmt to aus time (will need to change for dls)
	#if a message is sent in the evening with a small hour, or sent in the 
	#morning with a large hour, its probably afternoon (with a little wiggle room)
	print("hour:", hour, "created:", hour_sent)
	if hour >= 0 and hour <= 23 and (hour_sent > 17 and hour < 12 or hour_sent < 12 and hour > 12):
		return hour + 12
	return hour

def get_time_message(message_hour:int, message_min:int, created_hour:int):
	hour = get_24_hour_time(message_hour, created_hour)
	message = time_to_text(hour, message_min)
	if message_hour > 12 and message_hour < 24:
		message += " (24 hour time is the superior time 👍)"
	return message

@discordClient.event
async def on_message(message):
	if message.author == discordClient.user:
		return
	if discordClient.user in message.mentions:
		async with message.channel.typing():
			try:
				id = 0
				messages_row = cursor.execute("SELECT messages FROM chatgpt WHERE id = ?", (id,)).fetchone()
				prompt = cursor.execute("SELECT prompt FROM chatgpt_prompt").fetchone()[0]
				if messages_row:
					messages_list = json.loads(messages_row[0])
				else:
					print("we're starting the list again.")
					messages_list = []
					initial_message = {"role": "system", "content": prompt}
					messages_list.append(initial_message)
					dumped = json.dumps(messages_list)
					cursor.execute("INSERT INTO chatgpt VALUES (?, ?)", (id, dumped))
				new_message = {"role": "user", "content": str(message.content)}
				print(f"message content: {message.content}")
				messages_list.append(new_message)
				response = chatgpt_query(messages_list)
				messages_list.append(response.choices[0].message)
				print(f"messages list: {messages_list}")
				updated_messages_list = json.dumps(messages_list)
				cursor.execute("UPDATE chatgpt SET messages = ? WHERE id = ?", (updated_messages_list, id))
				total_tokens = response.usage.total_tokens
				cost = (total_tokens/1000) * 0.00175
				response_content = response.choices[0].message.content
				if len(response_content) >= 2000:
					print("message is too long, let's split it up")
					response_list = []
					offset = 0
					while offset < len(response_content):
						chunk = response_content[offset:offset+2000]
						reversed_chunk = chunk[::-1]
						length = reversed_chunk.find("\n")
						chunk = chunk[:2000 - length]
						offset += 2000 - length
						response_list.append(chunk)
					await message.reply(response_list[0], mention_author=False)
					for msg in response_list[1:]:
						await message.channel.send(msg)
				else:
					msg = await message.reply(response_content, mention_author=False)
					cursor.execute("INSERT INTO chatgpt_cost VALUES (?, ?)", (msg.id, cost))
			except Exception as e:
				await message.reply(e, mention_author=False)

	urls = re.findall(r'(https?:\/\/)([\w\-_]+(?:(?:\.[\w\-_]+)+))([\w\-\.,@?^=%&:/~\+#]*[\w\-\@?^=%&/~\+#])?', message.content)
	if urls:
		await asyncio.sleep(1)
		embeds = message.embeds
		if embeds:
			for embed in embeds:
				ocr = re.findall(r'(?i)aldi', detect_text_uri(embed.thumbnail.url))
				if ocr:
					pass
				if not ocr:
					logos = detect_logos_uri(embed.thumbnail.url)
					for logo in logos:
						cursor.execute("INSERT INTO ai VALUES (?, ?, ?)", [message.id, logo.description, logo.score])
					if logos:
						await message.add_reaction("👀")

	if not urls:
		if len(message.content) > 125:
			classify = classify_text(message.content)
			if classify:
				for category in classify:
					if category.confidence > 49:
						cursor.execute("INSERT INTO ai_text VALUES (?, ?, ?)", [message.id, category.name, category.confidence])
						await message.add_reaction("💡")
	
	for attachment in message.attachments:
		attachment_type, attch_format = attachment.content_type.split('/')
		if attachment_type == 'video':
			if attachment.size > 52428800:
				await message.channel.send("Video is >50MB and won't be posted to \#clips")
				return
			channel = discordClient.get_channel(int(os.getenv('CLIPS_CHANNEL')))
			button = Button(label="Jump", style=discord.ButtonStyle.link, url=message.jump_url)
			view = View()
			view.add_item(button)
			await channel.send(attachment.url, view=view)
		if attachment_type == 'audio':
			await attachment.save("audio.mp3")
			response = transcribe_audio("audio.mp3")
			await message.channel.send(response.text)
		if attachment_type == 'image':
			myuuid = str(uuid.uuid4())
			await attachment.save(myuuid)
			await asyncio.sleep(2)
			img = detect_text(myuuid)
			ocr = None
			if img:
				ocr = re.findall(r'(?i)aldi', img)
			if ocr:
				pass
			if not ocr:
				logos = detect_logos(myuuid)
				for logo in logos:
					cursor.execute("INSERT INTO ai VALUES (?, ?, ?)", [message.id, logo.description, logo.score])
				if logos:
					await message.add_reaction("👀")
				if not logos:
					labels = detect_labels(myuuid)
					for label in labels:
						cursor.execute("INSERT INTO ai VALUES (?, ?, ?)", [message.id, label.description, label.score])
						label.description = label.description.lower()
						if 'squirrel' in label.description:
							await message.channel.send("it's andrew")
							return
						if 'dog' in label.description:
							await message.channel.send("rat")
							return
						if 'electric blue' in label.description:
							await message.add_reaction("⚡")
							await message.add_reaction("🟦")
					if labels:
						await message.add_reaction("👀")
			if os.path.exists(myuuid):
				os.remove(myuuid)
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
	if reaction.emoji == "❓":
		id = reaction.message.id
		response = cursor.execute("SELECT cost FROM chatgpt_cost WHERE id = ?", (id,)).fetchone()
		total = cursor.execute("SELECT SUM(cost) FROM chatgpt_cost").fetchone()[0]
		if(response):
			await reaction.clear()
			await reaction.message.reply(f"Cost for this response was ${response[0]}\nTotal so far is ${total}")
	if reaction.emoji == "🤖":
		id = reaction.message.id
		if reaction.message.attachments:
			await reaction.clear()
			attachment = reaction.message.attachments[0]
			newuuid = str(uuid.uuid4())
			await attachment.save(f'{newuuid}.png')
			image_url = dalle_image_variation(newuuid)
			os.remove(f'{newuuid}.png')
			newuuid = str(uuid.uuid4())
			img = urllib.request.urlopen(image_url)
			img_data = img.read()
			with open(f'dalle/{newuuid}.png', "wb") as f:
				f.write(img_data)
			msg = await reaction.message.reply(file=discord.File(f'dalle/{newuuid}.png'))
			os.remove(f'dalle/{newuuid}.png')
			cost = 0.02
			cursor.execute("INSERT INTO chatgpt_cost VALUES (?, ?)", (msg.id, cost))

@discordClient.event
async def on_member_update(before, after):
    if before == discordClient.user or not after.nick:
        return
    if re.search(aldi_regex, after.nick):
        await after.edit(nick='loser')

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

sys.stdout.write = send_stdout_to_discord
sys.stderr.write = send_stdout_to_discord

discordClient.run(os.getenv('TOKEN'))