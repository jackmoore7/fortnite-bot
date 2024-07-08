import os
import signal

import main
import imports.api.api_epic as api_epic
from commands import is_owner

async def edit_message(ctx, id, content):
	try:
		if not is_owner(ctx):
			await ctx.respond(main.nice_try)
		else:
			channel = ctx.channel
			msg = await channel.fetch_message(id)
			await msg.edit(content=content)
			await ctx.respond("Edit successful.", ephemeral=True)

	except Exception as e:
		await ctx.respond(e, ephemeral=True)

async def stop_task(ctx, task_name):
	if not is_owner(ctx):
		await ctx.respond(main.nice_try)
	else:
		try:
			task = main.tasks_list.get(task_name)
			if task:
				task.cancel()
				await ctx.respond(f"{task} stopped ✅")
			else:
				await ctx.respond(f"{task_name} not found.")
		except Exception as e:
			await ctx.respond(f"Task couldn't be stopped: {e}")

async def add_friend(ctx, user_id):
	if not is_owner(ctx):
		await ctx.respond(main.nice_try)
	else:
		e = api_epic.add_friend(user_id)
		await ctx.respond(e)

async def list_friends(ctx, include_pending):
	if not is_owner(ctx):
		await ctx.respond(main.nice_try)
	else:
		e = api_epic.get_all_friends(include_pending)
		await ctx.respond(e)

async def purge(ctx, amount):
	if not is_owner(ctx):
		await ctx.respond(main.nice_try)
		return
	await ctx.defer()
	await ctx.channel.purge(limit=int(amount)+1, bulk=True)

async def sql_fetchall(ctx, query):
	print(ctx.user.id)
	if not is_owner(ctx):
		await ctx.respond(main.nice_try)
	else:
		try:
			q = main.cursor.execute(query).fetchall()
			await ctx.respond(q)
		except Exception as e:
			await ctx.respond("Not a valid query. Reason: " + str(repr(e)))

async def sql(ctx, query):
	print(ctx.user.id)
	if not is_owner(ctx):
		await ctx.respond(main.nice_try)
	else:
		try:
			main.cursor.execute(query)
			await ctx.respond("Executed ✅")
		except Exception as e:
			await ctx.respond("Not a valid query. Reason: " + str(repr(e)))

async def delete_message_by_id(ctx, id):
	if not is_owner(ctx):
		await ctx.respond(main.nice_try)
		return
	try:
		channel = ctx.channel
		message = await channel.fetch_message(id)
		await message.delete()
		await ctx.respond("Deleted", ephemeral=True)
	except Exception as e:
		await ctx.respond(e)

async def die(ctx):
	if not is_owner(ctx):
		await ctx.respond(main.nice_try)
		return
	await ctx.respond("Death request received 🫡")
	os.kill(int(os.getpid()), signal.SIGKILL)
	await main.discord_client.close()