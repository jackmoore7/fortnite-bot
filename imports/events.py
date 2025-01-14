import os
import discord
from discord.ui import Button, View
from imports.core_utils import discord_client, cursor
import imports.helpers as helpers
import imports.api.api_openai as api_openai

async def message(message):
	if message.author == discord_client.user:
		return
	if helpers.embed_tweets(message):
		webhook = (await message.channel.webhooks())[0]
		await webhook.send(content=helpers.embed_tweets(message), username=message.author.name, avatar_url=message.author.avatar)
		await message.delete()
		return
	if discord_client.user in message.mentions or str(message.channel.type) == 'private':
		async with message.channel.typing():
			contents = []
			user_info = {
				"name": message.author.display_name,
				"roles": [role.name for role in message.author.roles],
				"joined_at": message.author.joined_at.strftime("%Y-%m-%d") if message.author.joined_at else "Unknown",
			}
			channel_info = {
				"name": message.channel.name if hasattr(message.channel, 'name') else "DM",
				"type": str(message.channel.type),
				"topic": message.channel.topic if hasattr(message.channel, 'topic') and message.channel.topic else "",
			}
			contents.append({"role": "system", "content": ""})
			if message.reference:
				referenced = await message.channel.fetch_message(message.reference.message_id)
				messages = [message, referenced]
			else:
				messages = await message.channel.history(limit=10).flatten()
			messages.reverse()
			for msg in messages:
				content = [{"type": "text", "text": msg.content}]
				if msg.embeds:
					for embed in msg.embeds:
						if embed.thumbnail and embed.thumbnail.url:
							content.append({
								"type": "image_url",
								"image_url": {"url": embed.thumbnail.url}
							})
				if msg.attachments:
					for attachment in msg.attachments:
						if attachment.content_type and attachment.content_type.startswith('image/'):
							content.append({
								"type": "image_url",
								"image_url": {"url": attachment.url}
							})
				contents.append({
					"role": "user" if msg.author != discord_client.user else "assistant",
					"name": msg.author.display_name,
					"content": content if len(content) > 1 else msg.content
				})
			response = api_openai.openai_chat(contents, user_info, channel_info)
			
			try:
				cursor.execute(
					"CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, channel_id TEXT, message TEXT, response TEXT, timestamp DATETIME)"
				)
				cursor.execute(
					"INSERT INTO chat_history (user_id, channel_id, message, response, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
					(str(message.author.id), str(message.channel.id), message.content, response)
				)
			except Exception as e:
				print(f"Failed to store chat history: {e}")
				
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