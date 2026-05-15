import os

from imports.helpers import added, removed

async def sunscreen(ctx):
	role = ctx.guild.get_role(int(os.getenv('SUNSCREEN_ROLE')))
	if not role:
		await ctx.respond("This command doesn't work in this server.")
		return
	if role in ctx.user.roles:
		await ctx.user.remove_roles(role)
		await ctx.respond(removed)
	else:
		await ctx.user.add_roles(role)
		await ctx.respond(added)

async def fortnite_update(ctx):
	upd8 = ctx.guild.get_role(int(os.getenv('UPD8_ROLE')))
	if upd8 in ctx.user.roles:
		await ctx.user.remove_roles(upd8)
		await ctx.respond(removed)
	else:
		await ctx.user.add_roles(upd8)
		await ctx.respond(added)