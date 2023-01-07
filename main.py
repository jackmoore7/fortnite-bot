import os
import requests
import shutil
import discord
import re
import random
import uuid
import asyncio
import feedparser
from io import BytesIO
from discord.ext import tasks
from discord.ui import Button, View
import sqlite3 as sl
import datetime
from datetime import timezone
from dotenv import load_dotenv
import glob

load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=os.getenv('GOOGLE_KEY')

from vision import *
from API import *
from key_handling import *

intents = discord.Intents.all()
intents.members = True

discordClient = discord.Bot(intents=intents)

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

@discordClient.event
async def on_ready():
	print(f'{discordClient.user} is now online!')
	await discordClient.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="for <store>"))
	fortnite_update_bg.start()
	tv_show_update_bg.start()
	fortnite_status_bg.start()
	# fortnite_shop_update.start()
	fortnite_shop_update_v2.start()

@tasks.loop(minutes=1)
async def fortnite_update_bg():
	try:
		channel = discordClient.get_channel(int(os.getenv('UPD8_CHANNEL')))
		channel2 = discordClient.get_channel(int(os.getenv('CRINGE_ZONE')))
		response = get_fortnite_update_manifest()
		if 'error' in response:
			await channel2.send("The following error occured while trying to get the Fortnite update manifest: " + str(response))
			return
		current_version = cursor.execute("SELECT * FROM aes").fetchall()[0][0]
		if current_version != response:
			cursor.execute("UPDATE aes SET version = ?", (response,))
			embed = discord.Embed(title="A new Fortnite update was just deployed")
			embed.set_footer(text="Use /update to subscribe to notifications")
			embed.add_field(name="Build", value=response, inline=False)
			await channel.send("<@&" + os.getenv('UPD8_ROLE') + ">", embed=embed)
	except Exception as e:
		print("Something went wrong: " + str(repr(e)) + "\nRestarting internal task in 1 minute.")
		await asyncio.sleep(60)
		fortnite_update_bg.restart()

@tasks.loop(minutes=30)
async def tv_show_update_bg():
	try:
		user = discordClient.get_user(int(os.getenv('ME')))
		url = os.getenv('SHOWRSS')
		feed = feedparser.parse(url)
		last_guid = cursor.execute("select * from rss").fetchall()[0][0]
		latest_guid = feed['entries'][0]['guid']
		if latest_guid != last_guid:
			rssembed = discord.Embed(title = "A new episode just released!")
			rssembed.add_field(name="Name", value=feed['entries'][0]['tv_raw_title'], inline=False)
			rssembed.add_field(name="Released", value=feed['entries'][0]['published'], inline=False)
			cursor.execute("UPDATE rss SET guid = ?", (latest_guid,))
			await user.send(embed = rssembed)
	except Exception as e:
		print("Something went wrong: " + str(repr(e)) + "\nRestarting internal task in 1 minute.")
		await asyncio.sleep(60)
		tv_show_update_bg.restart()

@tasks.loop(minutes=1)
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
		print("Something went wrong: " + str(repr(e)) + "\nRestarting internal task in 1 minute.")
		await asyncio.sleep(60)
		fortnite_status_bg.restart()

#@tasks.loop(time=datetime.time(hour=5, minute=30))
@tasks.loop(minutes=10)
async def fortnite_shop_update():
	try:
		channel = discordClient.get_channel(int(os.getenv('SHOP_CHANNEL')))
		r = fortnite_shop()
		uid = cursor.execute("SELECT uid FROM shop").fetchall()[0][0]
		new_uid = r['lastUpdate']['uid']
		if new_uid != uid:
			for item in r['shop']:
				#if item['previousReleaseDate'] is None:
				if item['previousReleaseDate'] != (datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1)).strftime('%Y-%m-%d'): #if previous release date isn't yesterday
					item_list = cursor.execute("SELECT item FROM shop_ping").fetchall()
					for cosmetic in item_list:
						cosmetic = cosmetic[0]
						if cosmetic.lower() in item['displayName'].lower():
							users = cursor.execute("SELECT id FROM shop_ping WHERE item = ?", (cosmetic,)).fetchall()
							for user in users:
								user = user[0]
								await channel.send("<@" + str(user) + ">, " + item['displayName'] + " is in the shop\nTriggered by your keyword: " + cosmetic)
					image = item['displayAssets'][0]['full_background']
					e = requests.get(image, stream = True)
					image_size = e.headers['Content-Length']
					newuuid = str(uuid.uuid4())
					with open(newuuid + ".png", "wb") as f:
						for chunk in e.iter_content(int(image_size)):
							f.write(chunk)
						await channel.send(file=discord.File(newuuid + ".png"))
						if os.path.exists(newuuid + ".png"):
							os.remove(newuuid + ".png")
			await channel.send("---")
			cursor.execute("UPDATE shop SET uid = ?", (new_uid,))
	except Exception as e:
		print("Something went wrong: " + str(repr(e)) + "\nRestarting internal task in 1 minute.")
		await asyncio.sleep(60)
		fortnite_shop_update.restart()

@tasks.loop(minutes=10)
async def fortnite_shop_update_v2():
	try:
		channel = discordClient.get_channel(int(os.getenv('SHOP_CHANNEL')))
		r = fortnite_shop()
		uid = cursor.execute("SELECT uid FROM shop").fetchall()[0][0]
		new_uid = r['lastUpdate']['uid']
		if new_uid != uid:
			today = []
			for item in r['shop']:
				image = item['displayAssets'][0]['full_background']
				name = item['displayName']
				toople = (image, name)
				today.append(toople)
			yesterday = cursor.execute("SELECT * FROM shop_content").fetchall()
			diff = []
			for item in today:
				if item not in yesterday:
					diff.append(item)
			if len(diff) < 1:
				await channel.send("The shop was just updated, but there are no new items. Length changed by " + str(len(diff)))
				cursor.execute("UPDATE shop SET uid = ?", (new_uid,))
				return
			for item in diff:
				e = requests.get(item[0], stream = True)
				await asyncio.sleep(0.5)
				image_size = e.headers['Content-Length']
				newuuid = str(uuid.uuid4())
				with open("temp_images/" + newuuid + ".png", "wb") as f:
					for chunk in e.iter_content(int(image_size)):
						f.write(chunk)
			await channel.send(f"A new shop rotation was just released. There are {len(diff)} new items.")
			for item in diff:
					item_list = cursor.execute("SELECT item FROM shop_ping").fetchall()
					for cosmetic in item_list:
						cosmetic = cosmetic[0]
						if cosmetic.lower() in item[1].lower():
							users = cursor.execute("SELECT id FROM shop_ping WHERE item = ?", (cosmetic,)).fetchall()
							for user in users:
								user = user[0]
								await channel.send("<@" + str(user) + ">, " + item[1] + " is in the shop\nTriggered by your keyword: " + cosmetic)
			files = glob.glob('temp_images/*.png')
			for f in files:
				await channel.send(file=discord.File(f))
				os.remove(f)
			await channel.send("---")


			cursor.execute("DELETE FROM shop_content")
			for item in diff:
				cursor.execute("INSERT INTO shop_content VALUES (?, ?)", (item[0], item[1]))
			cursor.execute("UPDATE shop SET uid = ?", (new_uid,))
	except Exception as e:
		print("Something went wrong ((V2)): " + str(repr(e)) + "\nRestarting internal task in 1 minute.")
		files = glob.glob('temp_images/*.png')
		for f in files:
			os.remove(f)
		await asyncio.sleep(60)
		fortnite_shop_update_v2.restart()
			
				


@discordClient.slash_command()
async def dc(ctx):
	voice_state = ctx.guild.voice_client
	if voice_state:
		await voice_state.disconnect()
		await ctx.respond(":thumbsup:", ephemeral=True)
	else:
		await ctx.respond("Not connected to a voice channel", ephemeral=True)

@discordClient.slash_command(description="[Owner] Clear messages")
async def purge(ctx, amount):
	if ctx.user.id != int(os.getenv('ME')):
		await ctx.respond("nice try bozo")
		return
	await ctx.defer()
	await ctx.channel.purge(limit=int(amount)+1, bulk=True)

@discordClient.slash_command(description="Get pinged when someone joins a voice channel")
async def pingme(ctx):
	id = ctx.user.id
	users = cursor.execute("SELECT * FROM pingme").fetchall()
	for user in users:
		if id == user[0]:
			cursor.execute("DELETE FROM pingme WHERE user = ?", (id,))
			await ctx.respond("Removed ✅")
			return
	cursor.execute("INSERT INTO pingme VALUES (?)", (id,))
	await ctx.respond("Added ✅")
	

notifyme = discordClient.create_group("notifyme", "Get notified when an item you want is in the shop")

@notifyme.command(description="Add or remove a cosmetic")
async def edit(ctx, item):
	if len(item) > 25:
		await ctx.respond("String must be less than 26 characters")
		return
	if 'aldi' in item:
		await ctx.respond("No")
		return
	text_check = re.findall(r'(?i)[^a-z0-9\s\-\']', item)
	if text_check:
		await ctx.respond("Not a valid string. [a-z0-9\s\-'] only.")
		return
	id = ctx.user.id
	if len(cursor.execute("SELECT * FROM shop_ping WHERE item = ? AND id = ?", (item, id)).fetchall()) > 0:
		try:
			cursor.execute("DELETE FROM shop_ping WHERE item = ? AND id = ?", (item, id))
			await ctx.respond("Removed ✅")
			return
		except:
			await ctx.respond("Something went wrong")
	try:
		cursor.execute("INSERT INTO shop_ping VALUES (?, ?)", (id, item))
		await ctx.respond("Added ✅")
	except:
		await ctx.respond("Something went wrong")

@notifyme.command(description="View the list of cosmetics you want notifications for")
async def list(ctx):
	id = ctx.user.id
	list = []
	items = cursor.execute("SELECT item FROM shop_ping WHERE id = ?", (id,)).fetchall()
	for item in items:
		list.append(item[0])
	await ctx.respond(list)

@discordClient.slash_command(description="Subscribe/unsubscribe to Fortnite status updates")
async def update(ctx):
	roles = ctx.user.roles
	upd8 = ctx.guild.get_role(int(os.getenv('UPD8_ROLE')))
	print(roles)
	for role in roles:
		if role == upd8:
			await ctx.user.remove_roles(upd8)
			await ctx.respond("Removed role")
			return
	await ctx.user.add_roles(upd8)
	await ctx.respond("Added role")

@discordClient.slash_command(description="Check a user's all-time Fortnite statistics")
async def fortnite(ctx, username):
	r = fortnite_br_stats(username)
	if r.json()['status'] == 403:
		await ctx.respond("`" + username + "`" + " set their stats to private")
		return
	if r.json()['status'] != 200:
		await ctx.respond("`" + username + "`" " doesn't exist or hasn't played any games yet")
		return
	name = r.json()['data']['account']['name']
	level = r.json()['data']['battlePass']['level']
	wins = r.json()['data']['stats']['all']['overall']['wins']
	top3 = r.json()['data']['stats']['all']['overall']['top3']
	top5 = r.json()['data']['stats']['all']['overall']['top5']
	top6 = r.json()['data']['stats']['all']['overall']['top6']
	top10 = r.json()['data']['stats']['all']['overall']['top10']
	top12 = r.json()['data']['stats']['all']['overall']['top12']
	top25 = r.json()['data']['stats']['all']['overall']['top25']
	kills = r.json()['data']['stats']['all']['overall']['kills']
	killspermin = r.json()['data']['stats']['all']['overall']['killsPerMin']
	killspermatch = r.json()['data']['stats']['all']['overall']['killsPerMatch']
	deaths = r.json()['data']['stats']['all']['overall']['deaths']
	kd = r.json()['data']['stats']['all']['overall']['kd']
	matches = r.json()['data']['stats']['all']['overall']['matches']
	winrate = r.json()['data']['stats']['all']['overall']['winRate']
	minutesplayed = r.json()['data']['stats']['all']['overall']['minutesPlayed']
	playersoutlived = r.json()['data']['stats']['all']['overall']['playersOutlived']
	lastmodified = r.json()['data']['stats']['all']['overall']['lastModified']

	embed = discord.Embed(title = "All time statistics for " + name)
	embed.add_field(name="Level (current season)", value=level, inline=False)
	embed.add_field(name="Wins", value=wins, inline=False)
	embed.add_field(name="Top 3", value=top3, inline=False)
	embed.add_field(name="Top 5", value=top5, inline=False)
	embed.add_field(name="Top 6", value=top6, inline=False)
	embed.add_field(name="Top 10", value=top10, inline=False)
	embed.add_field(name="Top 12", value=top12, inline=False)
	embed.add_field(name="Top 25", value=top25, inline=False)
	embed.add_field(name="Kills", value=kills, inline=False)
	embed.add_field(name="Kills per minute", value=killspermin, inline=False)
	embed.add_field(name="Kills per match", value=killspermatch, inline=False)
	embed.add_field(name="Deaths", value=deaths, inline=False)
	embed.add_field(name="K/D", value=kd, inline=False)
	embed.add_field(name="Matches", value=matches, inline=False)
	embed.add_field(name="Win rate", value=str(winrate)+"%", inline=False)
	embed.add_field(name="Minutes played", value=str(minutesplayed) + " (" + str(round(minutesplayed/1440, 2)) + " days)", inline=False)
	embed.add_field(name="Players outlived", value=playersoutlived, inline=False)
	embed.add_field(name="Last updated", value=lastmodified, inline=False)
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
				os.remove(newuuid + ".png") #remove the image when we're done with it
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
		except:
			await ctx.respond("Not a valid query.")

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
	chars = []
	for character in string:
		char = character.encode("utf-8").hex()
		chars.append(char)
	await ctx.respond(chars, ephemeral=True)

@discordClient.event
async def on_message(message):
	message.content = message.content.lower()
	if message.author == discordClient.user:
		return
	
	for character in message.content:
		char = character.encode("utf-8").hex()
		bl = cursor.execute("SELECT hex FROM blacklist WHERE hex = ?", (char,)).fetchall()
		if bl:
			await message.delete()
			return
		#print("Character: " + character + ". Hex: " + char)
		if len(char) > 2 and len(char) < 8:
			wl = cursor.execute("SELECT hex FROM whitelist WHERE hex = ?", (char,)).fetchall()
			if wl:
				continue
			print("Deleted a suspicious message: " + message.content + ". The character found was: " + character + " with a hex code of: " + char)
			await message.delete()
			return

	urls = re.findall(r'(https?:\/\/)([\w\-_]+(?:(?:\.[\w\-_]+)+))([\w\-\.,@?^=%&:/~\+#]*[\w\-\@?^=%&/~\+#])?', message.content)
	if urls:
		print("URL detected")
		await asyncio.sleep(1)
		embeds = message.embeds
		if embeds:
			print("Embed detected")
			for embed in embeds:
				print(embed.thumbnail.url)
				if embed.title:
					print(embed.title)
					title = embed.title.lower()
					if 'aldi' in title:
						print("Found Aldi text in embed title")
						await message.delete()
						return
				ocr = re.findall(r'(?i)aldi', detect_text_uri(embed.thumbnail.url))
				if ocr:
					try:
						print("Found Aldi text in image!")
						await message.delete()
						await message.channel.send("ALDI detected. Confidence: 1. 🖕") 
						return
					except:
						print("Couldn't delete image")
						return
				if not ocr:
					print("Couldn't find Aldi text. Searching for logo instead...")
					logos = detect_logos_uri(embed.thumbnail.url)
					for logo in logos:
						cursor.execute("INSERT INTO ai VALUES (?, ?, ?)", [message.id, logo.description, logo.score])
						logo.description = logo.description.lower()
						score = str(logo.score)
						if logo.description == 'aldi':
							await message.delete()
							await message.channel.send("ALDI detected. Confidence: " + score + ". 🖕")
							return
					if logos:
						await message.add_reaction("👀")
	
	message.content = re.sub('[^0-9a-zA-Z]+', '', message.content)
	message.content = (message.content.encode('ascii', 'ignore')).decode("utf-8")
	ree = re.findall(r'(?i)(a|4|@)\s*(l|1|i|\|)\s*d\s*(i|1|l)\s*', message.content)
	if ree:
		await message.delete()
		return
	
	for attachment in message.attachments:
		attachment_type, attch_format = attachment.content_type.split('/')
		if attachment_type == 'video':
			print("Contains video")
			if attachment.size > 52428800:
				await message.channel.send("Video is >50MB and won't be posted to \#clips")
				return
			channel = discordClient.get_channel(int(os.getenv('CLIPS_CHANNEL')))
			button = Button(label="Jump", style=discord.ButtonStyle.link, url=message.jump_url)
			view = View()
			view.add_item(button)
			await channel.send(attachment.url, view=view)
		if attachment_type == 'image':
			myuuid = str(uuid.uuid4())
			await attachment.save(myuuid)
			print("Image detected. Searching for Aldi...")
			await asyncio.sleep(2)
			img = detect_text(myuuid)
			ocr = None
			if img:
				ocr = re.findall(r'(?i)aldi', img)
			if ocr:
				try:
					print("Found Aldi text in image! (attachment)")
					await message.delete()
					await message.channel.send("ALDI detected. Confidence: 1. 🖕")
				except:
					print("Couldn't delete message")
			if not ocr:
				print("Couldn't find Aldi text. Searching for logo instead...")
				logos = detect_logos(myuuid)
				print(logos)
				for logo in logos:
					cursor.execute("INSERT INTO ai VALUES (?, ?, ?)", [message.id, logo.description, logo.score])
					logo.description = logo.description.lower()
					score = str(logo.score)
					if logo.description == 'aldi':
						print("Found Aldi logo")
						await message.delete()
						await message.channel.send("ALDI detected. Confidence: " + score + ". 🖕")
				if logos:
					await message.add_reaction("👀")
				if not logos:
					print("No logos detected. Searching for labels...")
					labels = detect_labels(myuuid)
					print(labels)
					for label in labels:
						cursor.execute("INSERT INTO ai VALUES (?, ?, ?)", [message.id, label.description, label.score])
						label.description = label.description.lower()
						if 'squirrel' in label.description:
							await message.channel.send("it's andrew")
							return
						if 'dog' in label.description:
							await message.channel.send("rat")
							return
						if 'store' in label.description:
							print("probably aldi")
							await message.delete()
							await message.channel.send("Might be <store> but who knows really. Confidence: not very high but it's worth the risk 🖕")
					if labels:
						await message.add_reaction("👀")
			if os.path.exists(myuuid):
				os.remove(myuuid) #remove the image when we're done with it
	if 'heh' in message.content.lower():
		emoji = discordClient.get_emoji(int(os.getenv('HEH_EMOJI')))
		await message.add_reaction(emoji)
	if 'perhaps' in message.content.lower():
		await message.add_reaction("🦀")
	if '@everyone' in message.content.lower() and not message.channel.permissions_for(message.author).mention_everyone:
		await message.channel.send(file=discord.File("assets/everyone.gif"))

@discordClient.event
async def on_voice_state_update(member, before, after):
	audios = ["assets/echo.mp3"]
	await asyncio.sleep(0.5)
	if member == discordClient.user:
		return
	voice_state = member.guild.voice_client
	if voice_state:
		return
	if before.channel == None:
		print(str(member) + " joined " + str(after.channel.id))
		users = cursor.execute("SELECT * from pingme").fetchall()
		for user in users:
			if member.id == user[0]:
				return
			else:
				await after.channel.send("<@" + str(user[0]) + ">, " + str(member) + " just joined.")
		if not voice_state:
			await after.channel.connect()
			voice_state = member.guild.voice_client
			voice_state.play(discord.FFmpegPCMAudio(executable=os.getenv('FFMPEG'), source=random.choice(audios)))
			await asyncio.sleep(2)
			await voice_state.disconnect()
	if (before.channel and after.channel) and (before.channel.id != after.channel.id) and not voice_state:
		print(str(member) + " switched from " + str(before.channel.id) + " to " + str(after.channel.id))
		await after.channel.connect()
		voice_state = member.guild.voice_client
		#await voice_state.move_to(after.channel)
		voice_state.play(discord.FFmpegPCMAudio(executable=os.getenv('FFMPEG'), source=random.choice(audios)))
		await asyncio.sleep(2)
		await voice_state.disconnect()
	if (after.channel == None) and (len(before.channel.members) > 0) and not voice_state:
		print(str(member) + " left " + str(before.channel.id))
		await before.channel.connect()
		voice_state = member.guild.voice_client
		voice_state.play(discord.FFmpegPCMAudio(executable=os.getenv('FFMPEG'), source=random.choice(audios)))
		await asyncio.sleep(2)
		await voice_state.disconnect()

@discordClient.event
async def on_raw_message_edit(payload):
	message = payload.cached_message
	if not message:
		channel = discordClient.get_channel(payload.channel_id)
		message = await channel.fetch_message(payload.message_id)
	edited_message = payload.data['content']
	for character in edited_message:
		char = character.encode("utf-8").hex()
		#print("Character: " + character + ". Hex: " + char)
		if len(char) > 2 and len(char) < 8:
			wl = cursor.execute("SELECT hex FROM whitelist WHERE hex = ?", (char,)).fetchall()
			if wl:
				continue
			print("Deleted a suspicious message: " + message.content + ". The character found was: " + character + " with a hex code of: " + char)
			await message.delete()
			return

	ree = re.findall(r'(?i)(a|4|@)\s*(l|1|i|\|)\s*d\s*(i|1|l)\s*', edited_message)
	if ree:
		await message.delete()
		return

@discordClient.event
async def on_reaction_add(reaction, user):
	if user == discordClient.user:
		return
	if reaction.emoji == "🇱" or reaction.emoji == "🇦" or reaction.emoji == "🇩" or reaction.emoji == "🇮" or reaction.emoji == "🅰️":
		await reaction.clear()
	id = reaction.message.id
	users = await reaction.users().flatten()
	for lad in users:
		if lad == discordClient.user and reaction.emoji == "👀":
			await reaction.clear()
			response = cursor.execute("SELECT guess, score FROM ai WHERE id = ?", (id,),).fetchall()
			# for resp in response:
			# 	await reaction.message.channel.send("Guess: " + resp[1] + "\nConfidence: " + str(resp[2]))
			await reaction.message.reply(str(response) + "\nRequested by " + user.mention, mention_author=False)

@discordClient.event
async def on_member_update(before, after):
	if before == discordClient.user:
		return
	if after.nick:
		ree = re.findall(r'(?i)(a|4|@)\s*(l|1|i|\|)\s*d\s*(i|1|l)\s*', after.nick)
	if ree:
		await after.edit(nick='loser')

discordClient.run(os.getenv('TOKEN'))