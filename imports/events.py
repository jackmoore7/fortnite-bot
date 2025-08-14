import os
import discord
from discord.ui import Button, View
from imports.core_utils import discord_client, cursor
import imports.helpers as helpers
import imports.api.api_openai as api_openai

async def message(message):
	if message.author == discord_client.user:
		return
	if message.channel.id == int(os.getenv('CRINGE_ZONE')):
		api_openai.add_to_thread(message)
	if helpers.embed_tweets(message):
		webhook = (await message.channel.webhooks())[0]
		await webhook.send(content=helpers.embed_tweets(message), username=message.author.name, avatar_url=message.author.avatar)
		await message.delete()
		return
	if discord_client.user in message.mentions and str(message.channel.type) != 'private':
		async with message.channel.typing():
			response = api_openai.create_run()
			await message.reply(response, mention_author=False)
	for attachment in message.attachments:
		attachment_type, _ = attachment.content_type.split('/')
		if attachment_type == 'video':
			link_message = attachment.url
			channel = discord_client.get_channel(int(os.getenv('CLIPS_CHANNEL')))
			button = Button(label="Jump", style=discord.ButtonStyle.link, url=message.jump_url)
			view = View()
			view.add_item(button)
			await channel.send(link_message, view=view)
			await message.add_reaction("✅")
		if attachment_type == 'audio':
			await attachment.save("audio.mp3")
			response = api_openai.transcribe_audio("audio.mp3")
			await message.channel.send(response.text)
	if 'heh' in message.content.lower():
		emoji = discord_client.get_emoji(int(os.getenv('HEH_EMOJI')))
		await message.add_reaction(emoji)
	if 'perhaps' in message.content.lower():
		await message.add_reaction("🦀")
	if '@everyone' in message.content.lower() and not message.channel.permissions_for(message.author).mention_everyone:
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
	if reaction.emoji == "👀" and user != discord_client.user:
		users = await reaction.users().flatten()
		if discord_client.user in users:
			await reaction.clear()
			message_id = reaction.message.id
			response = cursor.execute("SELECT guess, score FROM ai WHERE id = ?", (message_id,)).fetchall()
			await reaction.message.reply(str(response) + "\nRequested by " + user.mention, mention_author=False)
	if reaction.emoji == "💡" and user != discord_client.user:
		users = await reaction.users().flatten()
		if discord_client.user in users:
			await reaction.clear()
			message_id = reaction.message.id
			response = cursor.execute("SELECT guess, score FROM ai_text WHERE id = ?", (message_id,)).fetchall()
			await reaction.message.reply(str(response) + "\nRequested by " + user.mention, mention_author=False)

async def member_remove(member):
	channel = discord_client.get_channel(int(os.getenv('BEG_4_VBUCKS')))
	await channel.send(f"{member} just left the server. https://tenor.com/view/thanos-fortnite-takethel-dance-gif-12100688")

async def member_update(before, after):
	if before == discord_client.user or not after.nick:
		return
