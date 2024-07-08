import os
import asyncio
import requests
import shutil
import discord
import uuid

import main
import imports.api.api_epic as api_epic
import imports.api.api_third_party as api_third_party

async def get_id(ctx, username):
	await ctx.respond(api_third_party.get_account_id(username))

async def get_username(ctx, id):
	e = api_epic.get_user_by_id(id)
	await ctx.respond(e['displayName'])

async def get_last_online(ctx, username):
	await ctx.defer()
	account_id = api_third_party.get_account_id(username)
	await asyncio.sleep(3)
	e = api_epic.get_user_presence(account_id)
	if e:
		await ctx.respond(f"{username} was last online at {e}")
	else:
		await ctx.respond("That user isn't in my friends list.")

async def stats(ctx, username):
	r = api_third_party.fortnite_br_stats(username)
	if r.json()['status'] == 403:
		await ctx.respond("`" + username + "` set their stats to private")
		return
	if r.json()['status'] != 200:
		await ctx.respond("`" + username + "` doesn't exist or hasn't played any games yet")
		return
	data = r.json()['data']
	name = data['account']['name']
	level = data['battlePass']['level']
	embed = main.discord.Embed(title="All time statistics for " + name)
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

async def map(ctx):
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