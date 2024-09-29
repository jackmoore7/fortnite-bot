import os
import re
import discord

from discord.ext.pages import Paginator, Page

from imports.helpers import nice_try, removed, added
from imports.core_utils import cursor
import imports.api.api_coles as api_coles
import imports.api.api_lego as api_lego
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

def is_owner(ctx):
	return ctx.user.id == int(os.getenv('ME'))

'''
	Owner only commands
'''

def coles_edit_2(item_id):
	result = api_coles.get_items([item_id])
	result = result['items'][0]
	if result:
		item_id = result[0]
		name = result[1]
		brand = result[2]
		description = result[3]
		current_price = result[4]
		on_sale = result[5]
		available = result[6]
		result_db = api_coles.cursor.execute("SELECT * FROM coles_specials WHERE id = ?", (item_id,)).fetchone()
		if result_db:
			api_coles.cursor.execute("DELETE FROM coles_specials WHERE id = ?", (item_id,))
			return f"Removed {brand} {name} from your list"
		else:
			api_coles.cursor.execute("INSERT INTO coles_specials VALUES (?, ?, ?, ?, ?, ?, ?)", (item_id, name, brand, description, current_price, on_sale, available))
			return f"Added {brand} {name} to your list"
	else:
		return result

async def coles_edit(ctx, item_id):
	if not is_owner(ctx):
		await ctx.respond(nice_try)
	else:
		await ctx.defer()
		result = api_coles.get_items([item_id])
		result = result['items'][0]
		if result:
			item_id = result[0]
			name = result[1]
			brand = result[2]
			description = result[3]
			current_price = result[4]
			on_sale = result[5]
			available = result[6]
			result_db = api_coles.cursor.execute("SELECT * FROM coles_specials WHERE id = ?", (item_id,)).fetchone()
			if result_db:
				api_coles.cursor.execute("DELETE FROM coles_specials WHERE id = ?", (item_id,))
				await ctx.respond(f"Removed {brand} {name} from your list")
			else:
				api_coles.cursor.execute("INSERT INTO coles_specials VALUES (?, ?, ?, ?, ?, ?, ?)", (item_id, name, brand, description, current_price, on_sale, available))
				await ctx.respond(f"Added {brand} {name} to your list")
		else:
			await ctx.respond(result)

async def coles_list(ctx):
	if not is_owner(ctx):
		await ctx.respond(nice_try)
	else:
		try:
			tracked = api_coles.cursor.execute("SELECT * FROM coles_specials")
			embed = discord.Embed(title = "Items you're tracking")
			for item in tracked:
				item_id = item[0]
				name = item[1]
				brand = item[2]
				current_price = item[4]
				on_sale = item[5]
				available = item[6]
				compact_info = f"**Brand**: {brand}\n**Price**: ${current_price}\n**On special**: {'Yes' if on_sale else 'No'}\n**Availability**: {'Available' if available else 'Unavailable'}"
				embed.add_field(name=f"{item_id} - {name}", value=compact_info, inline=False)
			await ctx.respond(embed=embed)
		except Exception as e:
			await ctx.respond(f"Couldn't get list: {e}")

'''
	Coles commands
'''

async def coles_search(ctx, string):
	await ctx.defer()
	results = api_coles.search_item(string)

	class view(discord.ui.View):
		def __init__(self, item_id: int):
			super().__init__()
			self.item_id = item_id

		@discord.ui.button(label="Track", style=discord.ButtonStyle.primary, custom_id="track_button")
		async def button_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
			if is_owner(ctx):
				await interaction.response.send_message(coles_edit_2(self.item_id))
			else:
				await interaction.response.send_message("You don't have permission to edit this list.", ephemeral=True)

	if results:
		url = "https://productimages.coles.com.au/productimages"
		num_results = results['noOfResults']
		if num_results == 0:
			await ctx.respond("Your search returned no results.")
			return
		results = results['results']
		results_list = [(product['id'], product['name'], product['brand'], product['imageUris'][0]['uri']) for product in results if ('adId' not in product or not product['adId']) and 'id' in product]
		pages = []
		for item in results_list:
			embed = discord.Embed(title = f"{item[2]} {item[1]}")
			embed.set_image(url=url + item[3])
			embed.add_field(name="ID", value=item[0])
			embed.set_footer(text=f"Returned {num_results} results")
			pages.append(Page(content=f"{item[2]} {item[1]}", embeds=[embed], custom_view=view(item_id=item[0])))
		paginator = Paginator(pages=pages)
		await paginator.respond(ctx.interaction)
	else:
		await ctx.respond("Something went wrong. Please try again.")

async def generate_graph(ctx, id):
	await ctx.defer()
	data = cursor.execute("SELECT * FROM coles_price_history WHERE id = ?", (id,)).fetchall()
	if not data:
		await ctx.respond(f"No results for `{id}`")
		return

	timestamps = [datetime.strptime(item[2], '%Y-%m-%d %H:%M:%S') for item in data]
	values = [float(item[1]) for item in data]

	fig, ax = plt.subplots(figsize=(12, 6))

	bars = ax.bar(range(len(timestamps)), values, width=0.5, color='#E01A22')

	low_price = min(values)
	high_price = max(values)
	price_changes = len([i for i in range(1, len(values)) if values[i] != values[i-1]])
	different_prices = len(set(values))

	title = f"Price trend for {id}\nLow: \${low_price:.2f} | High: \${high_price:.2f} | {price_changes} price changes | {different_prices} different prices"
	ax.set_title(title, fontsize=12, fontweight='bold')
	# ax.set_ylabel("Price ($)", fontsize=10)

	ax.set_xticks(range(len(timestamps)))
	ax.set_xticklabels([t.strftime('%m/%d/%Y') for t in timestamps], rotation=0, ha='center')

	for bar in bars:
		height = bar.get_height()
		ax.text(bar.get_x() + bar.get_width()/2., height,
				f'${height:.2f}',
				ha='center', va='bottom')

	y_pos = ax.get_ylim()[0] + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.05
	for i, (bar, timestamp) in enumerate(zip(bars, timestamps)):
		if i == 0:
			continue
		days = (timestamps[i] - timestamps[i-1]).days
		ax.text(bar.get_x() + bar.get_width()/2., y_pos,
				f'{days}\nDays',
				ha='center', va='bottom', fontsize=8, color='white')

	ax.grid(axis='y', linestyle='--', alpha=0.7)

	plt.tight_layout()
	plt.savefig('plot.png', dpi=300, bbox_inches='tight')

	await ctx.edit(file=discord.File("plot.png"))

	if os.path.exists("plot.png"):
		os.remove("plot.png")

'''
	Notifyme commands
'''

async def notifyme_edit(ctx, item):
	if len(item) > 25:
		await ctx.respond("String must be less than 26 characters")
		return
	text_check = re.findall(r'(?i)[^a-z0-9\s\-\']', item)
	if text_check:
		await ctx.respond("Not a valid string. [a-z0-9\s\-'] only.")
		return
	user_id = ctx.user.id
	if len(cursor.execute("SELECT * FROM shop_ping WHERE item = ? AND id = ?", (item, user_id)).fetchall()) > 0:
		cursor.execute("DELETE FROM shop_ping WHERE item = ? AND id = ?", (item, user_id))
		await ctx.respond(removed)
		return
	cursor.execute("INSERT INTO shop_ping VALUES (?, ?)", (user_id, item))
	await ctx.respond(added)

async def notifyme_list(ctx):
	items = cursor.execute("SELECT item FROM shop_ping WHERE id = ?", (ctx.user.id,)).fetchall()
	items = [item[0] for item in items]
	await ctx.respond(items)

'''
	Lego commands
'''

async def lego_search(ctx, string):
	product_url = 'https://www.lego.com/en-au/product/'
	products = api_lego.search_lego_item(string)
	if products:
		pages = []
		num_results = products['total']
		results = products['results']
		for item in results:
			embed = discord.Embed(title=item['name'], url=product_url + item['slug'])
			embed.set_image(url=item['baseImgUrl'])
			embed.add_field(name="Price", value=item['variant']['price']['formattedAmount'], inline=True)
			embed.add_field(name="Availability", value=item['variant']['attributes']['availabilityText'])
			embed.set_footer(text=f"Returned {num_results} results")
			pages.append(Page(content=item['name'], embeds=[embed]))
		paginator = Paginator(pages=pages)
		await paginator.respond(ctx.interaction)
	else:
		await ctx.respond("Something went wrong. Please try again.")

async def lego_edit(ctx, id):
	await ctx.defer()
	result = api_lego.get_lego_item_by_id(id)
	result = result['data']['product']
	if result:
		name = result['name']
		image_url = result['baseImgUrl']
		slug = result['slug']
		availability = result['variant']['attributes']['availabilityText']
		on_sale = result['variant']['attributes']['onSale']
		price = result['variant']['price']['formattedAmount']
		result_db = cursor.execute("SELECT * FROM lego WHERE id = ?", (id,)).fetchone()
		if result_db:
			cursor.execute("DELETE FROM lego WHERE id = ?", (id,)).fetchone()
			await ctx.respond(f"Removed {name} from your list")
		else:
			cursor.execute("INSERT INTO lego VALUES (?, ?, ?, ?, ?, ?, ?)", (id, name, image_url, slug, availability, on_sale, price))
			await ctx.respond(f"Added {name} to your list")
	else:
		await ctx.respond(f"{id} didn't return any results :(")

async def lego_list(ctx):
	tracked = cursor.execute("SELECT * FROM lego")
	embed = discord.Embed(title = "Items you're tracking")
	for item in tracked:
		item_id = item[0]
		name = item[1]
		availability = item[4]
		on_sale = item[5]
		price = item[6]
		compact_info = f"**Name**: {name}\n**Price**: {price}\n**On special**: {'Yes' if on_sale else 'No'}\n**Availability**: {availability}"
		embed.add_field(name=f"{item_id} - {name}", value=compact_info, inline=False)
	await ctx.respond(embed=embed)