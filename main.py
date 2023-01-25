import os
import requests
import shutil
import discord
import re
import uuid
import asyncio
import feedparser
from discord.ext import tasks
from discord.ui import Button, View
import sqlite3 as sl
from dotenv import load_dotenv
import glob
import urllib.request
from num2words import num2words

load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=os.getenv('GOOGLE_KEY')

from gcloud import *
from third_party_api import *
from key_handling import *
from epic_api import *

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
	fortnite_shop_update_v2.start()

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

@tasks.loop(minutes=5)
async def fortnite_shop_update_v2():
	try:
		channel = discordClient.get_channel(int(os.getenv('SHOP_CHANNEL')))
		r = fortnite_shop()
		uid = cursor.execute("SELECT uid FROM shop").fetchone()[0]
		new_uid = r['lastUpdate']['uid']
		if new_uid != uid:
			today = [(item['displayAssets'][0]['full_background'], item['displayName']) for item in r['shop']]
			yesterday = cursor.execute("SELECT * FROM shop_content").fetchall()
			diff = [tup for tup in today if tup[1] not in (y[1] for y in yesterday)]
			if len(diff) < 1:
				await channel.send(f"The shop was just updated, but there are no new items. Length changed by {len(diff)}.")
				cursor.execute("UPDATE shop SET uid = ?", (new_uid,))
				return
			for item in diff:
				newuuid = str(uuid.uuid4())
				urllib.request.urlretrieve(item[0], 'temp_images/' + newuuid + '.png')
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
			await channel.send("---")
			cursor.execute("DELETE FROM shop_content")
			cursor.executemany("INSERT INTO shop_content VALUES (?, ?)", [(item[0], item[1]) for item in today])
			cursor.execute("UPDATE shop SET uid = ?", (new_uid,))
	except Exception as e:
		print(f"Something went wrong ((V2)): {e}\nRestarting internal task in 1 minute.")
		files = glob.glob('temp_images/*.png')
		for f in files:
			os.remove(f)
		await asyncio.sleep(60)
		fortnite_shop_update_v2.restart()

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
	id = getAccountID(username)
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

@discordClient.event
async def on_message(message):
	message.content = message.content.lower()
	if message.author == discordClient.user:
		return
	bl = [row[0] for row in cursor.execute("SELECT hex FROM blacklist").fetchall()]
	wl = [row[0] for row in cursor.execute("SELECT hex FROM whitelist").fetchall()]
	for character in message.content:
		char = character.encode("utf-8").hex()
		if (char in bl):
			await message.delete()
			return
		if len(char) > 2 and len(char) < 8 and (char not in wl):
			ch = discordClient.get_channel(int(os.getenv('TEST_CHANNEL')))
			await ch.send("Deleted a suspicious message: " + message.content + ". The character found was: " + character + " with a hex code of: " + char)
			await message.delete()
			return

	time = re.search(r'([0-1]?[0-9]|2[0-3]):[0-5][0-9]', message.content)
	if(time):
		time = time.group()
		time = time.split(":")
		if int(time[0]) <= 12:
			time[0] = int(time[0]) + 12
		if time[1] == "00":
			await message.channel.send(num2words(time[0]) + " o'clock")
		elif time[1] == "30":
			await message.channel.send("half past " + num2words(time[0]))
		else:
			await message.channel.send(num2words(time[1]) + " past " + num2words(time[0]))

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
						print("Found Aldi text in image!")
						await message.delete()
						await message.channel.send("ALDI detected. Confidence: 1. 🖕") 
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

	if not urls:
		if len(message.content) > 125:
			classify = classify_text(message.content)
			if classify:
				for category in classify:
					if category.confidence > 49:
						cursor.execute("INSERT INTO ai_text VALUES (?, ?, ?)", [message.id, category.name, category.confidence])
						await message.add_reaction("💡")

	message.content = re.sub(r'[^0-9a-zA-Z]+', '', message.content)
	message.content = message.content.encode('ascii', 'ignore').decode("utf-8")
	if re.search(r'(?i)(a|4|@)\s*(l|1|i|\|)\s*d\s*(i|1|l)\s*', message.content):
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
						if 'electric blue' in label.description:
							await message.add_reaction("⚡")
							await message.add_reaction("🟦")
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
async def on_raw_message_edit(payload):
	message = payload.cached_message
	if not message:
		channel = discordClient.get_channel(payload.channel_id)
		message = await channel.fetch_message(payload.message_id)
	edited_message = payload.data['content']
	bl = [row[0] for row in cursor.execute("SELECT hex FROM blacklist").fetchall()]
	wl = [row[0] for row in cursor.execute("SELECT hex FROM whitelist").fetchall()]
	for character in edited_message:
		char = character.encode("utf-8").hex()
		if (char in bl):
			await message.delete()
			return
		if len(char) > 2 and len(char) < 8 and (char not in wl):
			print("Deleted a suspicious message: " + message.content + ". The character found was: " + character + " with a hex code of: " + char)
			await message.delete()
			return

	if re.search(r'(?i)(a|4|@)\s*(l|1|i|\|)\s*d\s*(i|1|l)\s*', edited_message):
		await message.delete()

@discordClient.event
async def on_reaction_add(reaction, user):
	if user == discordClient.user:
		return
	bad_emoji = ["🇱", "🇦", "🇩", "🇮", "🅰️"]
	if reaction.emoji in bad_emoji:
		await reaction.clear()
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
    if re.search(r'(?i)(a|4|@)\s*(l|1|i|\|)\s*d\s*(i|1|l)\s*', after.nick):
        await after.edit(nick='loser')

discordClient.run(os.getenv('TOKEN'))