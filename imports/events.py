import os
import discord
from discord.ui import Button, View

import main
import helpers
import imports.api.api_openai as api_openai

async def message(message):
	if message.author == main.discord_client.user:
		return
	if helpers.embed_tweets(message):
		webhook = (await message.channel.webhooks())[0]
		await webhook.send(content=helpers.embed_tweets(message), username=message.author.name, avatar_url=message.author.avatar)
		await message.delete()
		return
	if main.discord_client.user in message.mentions or str(message.channel.type) == 'private':
		async with message.channel.typing():
			contents = []
			initial_message = {
				"role": "system",
				"content": "You're a helpful and decisive lad that LOVES Fortnite and answers any questions. Even if the questions aren't fortnite-related, you manage to sneak a Fortnite reference into each answer."
			}
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
									"role": "user" if msg.author != main.discord_client.user else "assistant",
									"content": [
										{"type": "text", "text": msg.author.display_name + ": " + msg.content if msg.author != main.discord_client.user else msg.content},
										{"type": "image_url", "image_url": {"url": embed.thumbnail.url, "detail": "high"}}
									]
								})
						except Exception:
							pass #probably no thumbnail url :/
				elif message.attachments:
					for attachment in msg.attachments:
						attachment_type, _ = attachment.content_type.split('/')
						if attachment_type == 'image':
							contents.append({
								"role": "user" if msg.author != main.discord_client.user else "assistant",
								"content": [
									{"type": "text", "text": msg.author.display_name + ": " + msg.content if msg.author != main.discord_client.user else msg.content},
									{"type": "image_url", "image_url": {"url": attachment.url, "detail": "high"}}
								]
							})
				else:
					user = "user" if msg.author != main.discord_client.user else "assistant"
					contents.append({"role": user, "content": msg.author.display_name + ": " + msg.content})
			await message.reply(api_openai.openai_chat(contents), mention_author=False)	
	for attachment in message.attachments:
		attachment_type, _ = attachment.content_type.split('/')
		if attachment_type == 'video':
			if attachment.size > 52428800:
				link_message = attachment.url + "Media is too large to embed - please jump to the original message"
			else:
				link_message = attachment.url
			channel = main.discord_client.get_channel(int(os.getenv('CLIPS_CHANNEL')))
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
		emoji = main.discord_client.get_emoji(int(os.getenv('HEH_EMOJI')))
		await message.add_reaction(emoji)
	if 'perhaps' in message.content.lower():
		await message.add_reaction("🦀")
	if '@everyone' in message.content.lower() and not message.channel.permissions_for(message.author).mention_everyone:
		await message.channel.send(file=discord.File("assets/everyone.gif"))

async def voice_state_update(member, before, after):
    if member == main.discord_client.user:
        return
    if before.channel is None and after.channel is not None:
        print(f"{member} joined {after.channel.id}")
        users = main.cursor.execute("SELECT * from pingme").fetchall()
        users_id = [user[0] for user in users]
        if member.id in users_id:
            return
        else:
            for user_id in users_id:
                await after.channel.send(f"<@{user_id}>, {member} just joined.")

async def reaction(reaction, user):
	if user == main.discord_client.user:
		return
	if reaction.emoji == "👀" and user != main.discord_client.user:
		users = await reaction.users().flatten()
		if main.discord_client.user in users:
			await reaction.clear()
			message_id = reaction.message.id
			response = main.cursor.execute("SELECT guess, score FROM ai WHERE id = ?", (message_id,)).fetchall()
			await reaction.message.reply(str(response) + "\nRequested by " + user.mention, mention_author=False)
	if reaction.emoji == "💡" and user != main.discord_client.user:
		users = await reaction.users().flatten()
		if main.discord_client.user in users:
			await reaction.clear()
			message_id = reaction.message.id
			response = main.cursor.execute("SELECT guess, score FROM ai_text WHERE id = ?", (message_id,)).fetchall()
			await reaction.message.reply(str(response) + "\nRequested by " + user.mention, mention_author=False)

async def member_remove(member):
	channel = main.discord_client.get_channel(int(os.getenv('BEG_4_VBUCKS')))
	await channel.send(f"{member} just left the server. https://tenor.com/view/thanos-fortnite-takethel-dance-gif-12100688")

async def member_update(before, after):
	if before == main.discord_client.user or not after.nick:
		return
	
# async def message_old(message):
# 	if message.author == main.discordClient.user and message.reference:
# 		message_author = "assistant"
# 		print("Message is a reply from bot to user, so it should be added to the thread.")
# 	elif message.author == main.discordClient.user and not message.reference:
# 		return
# 	else:
# 		message_author = "user"
# 	if message.attachments:
# 		for attachment in message.attachments:
# 			attachment_type, _ = attachment.content_type.split('/')
# 			if attachment_type == 'image':
# 				openai_api.add_to_thread(message_author, [
# 										{"type": "text", "text": message.author.display_name + ": " + message.content if message.author != main.discordClient.user else message.content},
# 										{"type": "image_url", "image_url": {"url": attachment.url, "detail": "high"}}
# 									])
# 			if attachment_type == 'video':
# 				if attachment.size > 52428800:
# 					await message.add_reaction("❌")
# 					return
# 				channel = main.discordClient.get_channel(int(os.getenv('CLIPS_CHANNEL')))
# 				button = Button(label="Jump", style=discord.ButtonStyle.link, url=message.jump_url)
# 				view = View()
# 				view.add_item(button)
# 				await channel.send(attachment.url, view=view)
# 				await message.add_reaction("✅")
# 	elif message.embeds:
# 		for embed in message.embeds:
# 			try:
# 				openai_api.add_to_thread(message_author, [
# 											{"type": "text", "text": message.author.display_name + ": " + message.content if message.author != main.discordClient.user else message.content},
# 											{"type": "image_url", "image_url": {"url": embed.thumbnail.url, "detail": "high"}}
# 										])
# 			except Exception:
# 				try:
# 					openai_api.add_to_thread(message_author, message.content)
# 				except Exception:
# 					pass #no message content
# 	else:
# 		openai_api.add_to_thread(message_author, message.content)
# 	if main.discordClient.user in message.mentions or str(message.channel.type) == 'private':
# 		async with message.channel.typing():
# 			await message.reply(openai_api.create_run())
# 	if 'heh' in message.content.lower():
# 		emoji = main.discordClient.get_emoji(int(os.getenv('HEH_EMOJI')))
# 		await message.add_reaction(emoji)
# 	if 'perhaps' in message.content.lower():
# 		await message.add_reaction("🦀")
# 	if '@everyone' in message.content.lower() and not message.channel.permissions_for(message.author).mention_everyone:
# 		await message.channel.send(file=discord.File("assets/everyone.gif"))