import sqlite3 as sl
import discord

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

intents = discord.Intents.all()
intents.members = True
discord_client = discord.Bot(intents=intents)

tasks_list = {}