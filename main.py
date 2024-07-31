import os
import sys
import asyncio
import faulthandler
import signal
import logging
import heartrate

from dotenv import load_dotenv
from systemd.journal import JournalHandler
from imports.core_utils import discord_client

import imports.tasks1 as bg_tasks
import imports.commands as cmd
import imports.slash_commands.cmd_owner as owner_cmd
import imports.slash_commands.cmd_fortnite as fortnite_cmd
import imports.slash_commands.cmd_notifyme as notifyme_cmd
import imports.slash_commands.cmd_misc as misc_cmd
import imports.events as events

heartrate.trace(browser=True, host='0.0.0.0')

log = logging.getLogger('demo')
log.addHandler(JournalHandler())
log.setLevel(logging.INFO)
log.info('sent to journal')

logging.basicConfig(level=logging.INFO)

faulthandler.enable(file=open('error.log', 'w'))
faulthandler.register(signal.SIGUSR1.value)

load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"]=os.getenv('GOOGLE_KEY')

@discord_client.event
async def on_ready():
	await bg_tasks.tasks_on_ready()

'''
	Grouped commands - for coles, shop notifications, and lego
'''

coles_group = discord_client.create_group("coles", "Edit your tracked items list")
notifyme_group = discord_client.create_group("notifyme", "Get notified when an item you want is in the shop")
lego_group = discord_client.create_group("lego")

@coles_group.command(description="[Owner] Add or remove an item")
async def edit(ctx, item_id):
	await cmd.coles_edit(ctx, item_id)

@coles_group.command(description="[Owner] View your tracked items")
async def list(ctx):
	await cmd.coles_list(ctx)

@coles_group.command(description="Search a Coles item by name")
async def search(ctx, string):
	await cmd.coles_search(ctx, string)

@coles_group.command(description="View the price over time of a tracked item")
async def graph(ctx, id):
	await cmd.generate_graph(ctx, id)

@notifyme_group.command(description="Add or remove a cosmetic")
async def edit(ctx, item):
	await cmd.notifyme_edit(ctx, item)

@notifyme_group.command(description="View the list of cosmetics you want notifications for")
async def list(ctx):
	await cmd.notifyme_list(ctx)

@lego_group.command(description="Search a Lego item")
async def search(ctx, string):
	await cmd.lego_search(ctx, string)

@lego_group.command(description="Add or remove an item")
async def edit(ctx, id):
	await cmd.lego_edit(ctx, id)

@lego_group.command(description="View your tracked items")
async def list(ctx):
	await cmd.lego_list(ctx)

'''
	Slash commands that are only used by the owner
'''

@discord_client.slash_command(description="[Owner] Edit a message")
async def edit_message(ctx, id, content):
	await owner_cmd.edit_message(ctx, id, content)

@discord_client.slash_command(description="[Owner] Stop an internal task")
async def stop_task(ctx, task_name):
	await owner_cmd.stop_task(ctx, task_name)

@discord_client.slash_command(description="[Owner] Add friend")
async def add_friend(ctx, user_id):
	await owner_cmd.add_friend(ctx, user_id)

@discord_client.slash_command(description="[Owner] List all friends")
async def list_friends(ctx, include_pending=''):
	await owner_cmd.list_friends(ctx, include_pending)

@discord_client.slash_command(description="[Owner] Clear messages")
async def purge(ctx, amount):
	await owner_cmd.purge(ctx, amount)

@discord_client.slash_command(description="[Owner] Query the database with an SQL command")
async def sql_fetchall(ctx, query):
	await owner_cmd.sql_fetchall(ctx, query)

@discord_client.slash_command(description="[Owner] Query the database with an SQL command")
async def sql(ctx, query):
	await owner_cmd.sql(ctx, query)

@discord_client.slash_command(description="[Owner] Delete a message by ID")
async def delete_message_by_id(ctx, id):
	await owner_cmd.delete_message_by_id(ctx, id)

@discord_client.slash_command(description="[Owner] SIGKILL the bot's PID")
async def die(ctx):
	await owner_cmd.die(ctx)

'''
	Slash commands that can be used by anyone
'''

@discord_client.slash_command(description="Get a user's Epic Games ID")
async def fortnite_get_id(ctx, username):
	await fortnite_cmd.get_id(ctx, username)

@discord_client.slash_command(description="Get Epic Games username by ID")
async def get_username(ctx, id):
	await fortnite_cmd.get_username(ctx, id)

@discord_client.slash_command(description="Return when a user was last online")
async def get_last_online(ctx, username):
	await fortnite_cmd.get_last_online(ctx, username)

@discord_client.slash_command(description="Check a user's all-time Fortnite statistics")
async def fortnite(ctx, username):
	await fortnite_cmd.stats(ctx, username)

@discord_client.slash_command(description="View the current Battle Royale map")
async def fortnite_map(ctx):
	await fortnite_cmd.map(ctx)

@discord_client.slash_command(description="Get pinged for sun protection forecasts")
async def sunscreen(ctx):
	await notifyme_cmd.sunscreen(ctx)

@discord_client.slash_command(description="Subscribe/unsubscribe to Fortnite status updates")
async def update(ctx):
	await notifyme_cmd.fortnite_update(ctx)

@discord_client.slash_command(description="Check the bot's ping")
async def ping(ctx):
	await misc_cmd.ping(ctx)
	
@discord_client.slash_command(description="Generate an image with DALL-E 3")
async def dalle3(ctx, prompt):
	await misc_cmd.dalle3(ctx, prompt)
	
@discord_client.slash_command(description="Train game - get to target using +-*/^")
async def train_game(ctx, number, target=10):
	await misc_cmd.train_game(ctx, number, target)

'''
	Discord events
'''

@discord_client.event
async def on_message(message):
	await events.message(message)

@discord_client.event
async def on_voice_state_update(member, before, after):
	await events.voice_state_update(member, before, after)

@discord_client.event
async def on_reaction_add(reaction, user):
	await events.reaction(reaction, user)

@discord_client.event
async def on_member_remove(member):
	await events.member_remove(member)

@discord_client.event
async def on_member_update(before, after):
    await events.member_update(before, after)

# @discordClient.event
# async def on_message(message):
# 	events.message_old(message)

'''
	Discord handling
'''

def send_stdout_to_discord(message):
	message = message.strip()
	if message:
		channel = discord_client.get_channel(int(os.getenv('STDOUT')))
		if channel:
			asyncio.ensure_future(channel.send(message))

def send_stdout_to_discord(message):
    message = message.strip()

    if message:
        channel = discord_client.get_channel(int(os.getenv('STDOUT')))
        
        if channel:
            if len(message) > 2000:
                chunks = [message[i:i+2000] for i in range(0, len(message), 2000)]
                
                for chunk in chunks:
                    asyncio.ensure_future(channel.send(chunk))
            else:
                asyncio.ensure_future(channel.send(message))

sys.stdout.write = send_stdout_to_discord
sys.stderr.write = send_stdout_to_discord

discord_client.run(os.getenv('TOKEN'))