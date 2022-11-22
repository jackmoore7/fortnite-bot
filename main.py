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
import datetime
from dotenv import load_dotenv

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
	await discordClient.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="your ass"))
	fortnite_update_bg.start()
	tv_show_update_bg.start()
	fortnite_status_bg.start()
	fortnite_shop_update.start()

@tasks.loop(minutes=1)
async def fortnite_update_bg():
	channel = discordClient.get_channel(int(os.getenv('UPD8_CHANNEL')))
	response = get_fortnite_update_manifest()
	current_version = cursor.execute("SELECT * FROM aes").fetchall()[0][0]
	if current_version != response:
		cursor.execute("UPDATE aes SET version = ?", (response,))
		embed = discord.Embed(title="A new Fortnite update was just deployed")
		embed.set_footer(text="Use /update to subscribe to notifications")
		embed.add_field(name="Build", value=response, inline=False)
		await channel.send("<@&" + os.getenv('UPD8_ROLE') + ">", embed=embed)

@tasks.loop(minutes=30)
async def tv_show_update_bg():
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

@tasks.loop(minutes=1)
async def fortnite_status_bg():
	channel = discordClient.get_channel(int(os.getenv('UPD8_CHANNEL')))
	response = get_fortnite_status()
	current_status = cursor.execute("SELECT * FROM server").fetchall()[0][0]
	if current_status != response:
		cursor.execute("UPDATE server SET status = ?", (response,))
		embed = discord.Embed(title = "Fortnite server status update")
		embed.set_footer(text="Use /update to subscribe to notifications")
		embed.add_field(name="Status", value=response)
		await channel.send("<@&" + os.getenv('UPD8_ROLE') + ">", embed=embed)

@tasks.loop(time=datetime.time(hour=0, minute=1))
async def fortnite_shop_update():
	channel = discordClient.get_channel(int(os.getenv('SHOP_CHANNEL')))
	async with channel.typing():
		url = "https://fortniteapi.io/v2/shop?lang=en"
		key = os.getenv('FNAPI_IO_KEY')
		r = requests.get(url, headers={"Authorization": key})
		r = r.json()
		for item in r['shop']:
			image = item['displayAssets'][0]['full_background']
			e = requests.get(image, stream = True)
			newuuid = str(uuid.uuid4())
			with open(newuuid + ".png", "wb") as f:
				shutil.copyfileobj(e.raw, f)
				if 'peely' in item['displayName']:
					await channel.send("<@" + os.getenv('ANDY') + ">", file=discord.File(newuuid + ".png"))
				else:
					await channel.send(file=discord.File(newuuid + ".png"))
				if os.path.exists(newuuid + ".png"):
					os.remove(newuuid + ".png")
		print("finished shop post")

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
		except:
			await ctx.respond("Not a valid query.")

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
	await asyncio.sleep(0.5)
	if member == discordClient.user:
		return
	voice_state = member.guild.voice_client
	if voice_state:
		return
	if before.channel == None:
		print(str(member) + " joined " + str(after.channel.id))
		if not voice_state:
			await after.channel.connect()
			voice_state = member.guild.voice_client
			voice_state.play(discord.FFmpegPCMAudio(executable=os.getenv('FFMPEG'), source="assets/echo.mp3"))
			await asyncio.sleep(2)
			await voice_state.disconnect()
	if (before.channel and after.channel) and (before.channel.id != after.channel.id) and not voice_state:
		print(str(member) + " switched from " + str(before.channel.id) + " to " + str(after.channel.id))
		await after.channel.connect()
		voice_state = member.guild.voice_client
		#await voice_state.move_to(after.channel)
		voice_state.play(discord.FFmpegPCMAudio(executable=os.getenv('FFMPEG'), source="assets/echo.mp3"))
		await asyncio.sleep(2)
		await voice_state.disconnect()
	if (after.channel == None) and (len(before.channel.members) > 0) and not voice_state:
		print(str(member) + " left " + str(before.channel.id))
		await before.channel.connect()
		voice_state = member.guild.voice_client
		voice_state.play(discord.FFmpegPCMAudio(executable=os.getenv('FFMPEG'), source="assets/echo.mp3"))
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
	id = reaction.message.id
	users = await reaction.users().flatten()
	for lad in users:
		if lad == discordClient.user and reaction.emoji == "👀":
			await reaction.clear()
			response = cursor.execute("SELECT guess, score FROM ai WHERE id = ?", (id,),).fetchall()
			# for resp in response:
			# 	await reaction.message.channel.send("Guess: " + resp[1] + "\nConfidence: " + str(resp[2]))
			await reaction.message.reply(response, mention_author=False)


discordClient.run(os.getenv('TOKEN'))