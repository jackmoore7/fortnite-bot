import os

import discord

import imports.api.api_openai as api_openai
import imports.helpers as helpers
from imports.core_utils import discord_client

cringe_zone = int(os.getenv("CRINGE_ZONE"))
clips_channel = int(os.getenv("CLIPS_CHANNEL"))
clip_message_map = {}
clip_blacklist = ["www.tiktok.com", "fxtwitter.com"]

async def publish_clip(source_message):
	if any(blacklisted in source_message.content.lower() for blacklisted in clip_blacklist):
		return
	channel = discord_client.get_channel(clips_channel)
	clip_message = await source_message.forward_to(channel)
	clip_message_map.setdefault(source_message.id, []).append(clip_message.id)
	await source_message.add_reaction("✅")
	return clip_message

async def message(message):
	if message.author == discord_client.user:
		return
	if message.channel.id == cringe_zone:
		api_openai.add_to_thread(message)
	if helpers.embed_tweets(message):
		webhook = (await message.channel.webhooks())[0]
		await webhook.send(content=helpers.embed_tweets(message), username=message.author.name, avatar_url=message.author.avatar)
		await message.delete()
		return
	if discord_client.user in message.mentions and str(message.channel.type) != "private" and message.channel.id == cringe_zone:
		async with message.channel.typing():
			response = api_openai.create_run()
			await message.reply(response, mention_author=False)
	for attachment in message.attachments:
		attachment_type, _ = attachment.content_type.split("/")
		if attachment_type == "video":
			await publish_clip(message)
		if attachment_type == "audio":
			await attachment.save("audio.mp3")
			response = api_openai.transcribe_audio("audio.mp3")
			await message.channel.send(response.text)
	if "heh" in message.content.lower():
		emoji = discord_client.get_emoji(int(os.getenv("HEH_EMOJI")))
		await message.add_reaction(emoji)
	if "perhaps" in message.content.lower():
		await message.add_reaction("🦀")
	if "@everyone" in message.content.lower() and not message.channel.permissions_for(message.author).mention_everyone:
		await message.channel.send(file=discord.File("assets/everyone.gif"))

async def voice_state_update(member, before, after):
	if member == discord_client.user:
		return
	if before.channel is None and after.channel is not None:
		print(f"{member} joined {after.channel.id}")

async def reaction(reaction, user):
	if user == discord_client.user:
		return
	try:
		api_openai.add_reaction(reaction, user)
	except Exception as e:
		print("Failed to record reaction in thread buffer:", e)
	if reaction.emoji == "✅" and reaction.message.id in clip_message_map and (user == reaction.message.author or user.id == os.getenv("ME")):
		clip_ids = clip_message_map.pop(reaction.message.id, [])
		channel = discord_client.get_channel(clips_channel)
		if channel:
			for clip_id in clip_ids:
				try:
					clip_message = await channel.fetch_message(clip_id)
					await clip_message.delete()
				except Exception:
					pass
		await reaction.clear()

async def member_remove(member):
	channel = discord_client.get_channel(int(os.getenv("BEG_4_VBUCKS")))
	await channel.send(f"{member} just left the server", file=discord.File("assets/takethel.gif"))

async def on_message_edit(before, after):
	if after.author == discord_client.user:
		return
	if after.channel.id == cringe_zone:
		api_openai.add_edit_to_thread(before, after)
	if not before.embeds and after.embeds:
		print("after.embeds triggered")
		embed = after.embeds[0]
		if embed.type == "video":
			await publish_clip(after)

# async def member_update(before, after):
# 	if before == discord_client.user or not after.nick:
# 		pass
