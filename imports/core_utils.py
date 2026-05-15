import sqlite3 as sl
import discord
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv() # apparently I need to load dotenv here as well even though it's already loaded in main. how interesting!

mongo_client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
print("mongo client: " + str(mongo_client))

con = sl.connect('fortnite.db', isolation_level=None)
cursor = con.cursor()

intents = discord.Intents.all()
intents.members = True
discord_client = discord.Bot(intents=intents)

tasks_list = {}