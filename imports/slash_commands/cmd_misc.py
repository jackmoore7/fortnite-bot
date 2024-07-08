import itertools
import copy

import main
import imports.api.api_openai as api_openai
import helpers

async def ping(ctx):
	await ctx.respond("Ponged your ping in " + str(round(main.discord_client.latency * 1000)) + "ms 😳")

async def dalle3(ctx, prompt):
	await ctx.defer()
	await ctx.respond(api_openai.dalle_prompt(prompt))

async def get_to_ten(ctx, number):
	try:
		if len(number) != 4:
			await ctx.respond("Please give a four digit number (0000-9999)")
		else:
			a = int(number[0]) # these will raise an exception if they can't convert
			b = int(number[1])
			c = int(number[2])
			d = int(number[3])
			response = helpers.get_to_x(10, a, b, c, d)
			response = helpers.format_train_solution(response)
			if len(response) == 0:
				await ctx.respond("There are no solutions for `" + str(number) + "`")
			else:
				embed = main.discord.Embed(title="Results for train game with number " + str(number))
				title = "All " + str(len(response)) + " solutions"
				embed.add_field(name=title, value=response)
				await ctx.respond(response)
	except Exception as e:
		await ctx.respond(f"ruh roh {e}")

'''
	Helper methods
'''

def attempt_get_x(x, nums, current_total, current_operations:list[str]):
	successions = []
	if len(nums) < 1 or len(nums) > 4: # something wrong happened
		return successions
	
	# remove the first item cause we're using it now
	current_num = nums[0]
	nums = nums[1:]
	
	if len(nums) == 3: # first number (remember, we took one off)
		attempt = attempt_get_x(x, nums, current_num, [str(current_num)])
		if attempt is not None:
			successions.append(attempt)
	else:
		# make a new copy of what we've done, then add on what we're going to do
		ops_add = copy.deepcopy(current_operations)
		ops_sub = copy.deepcopy(current_operations)
		ops_mul = copy.deepcopy(current_operations)
		ops_div = copy.deepcopy(current_operations)
		ops_pow = copy.deepcopy(current_operations)

		ops_add.append('+')
		ops_sub.append('-')
		ops_mul.append('*')
		ops_div.append('/')
		ops_pow.append('^')

		ops_add.append(str(current_num))
		ops_sub.append(str(current_num))
		ops_mul.append(str(current_num))
		ops_div.append(str(current_num))
		ops_pow.append(str(current_num))

		if len(nums) == 0: # last number, no more recursion
			if ops_add is not None and current_total + current_num == x:
				successions.append(ops_add)
			if ops_sub is not None and current_total - current_num == x:
				successions.append(ops_sub)
			if ops_mul is not None and current_total * current_num == x:
				successions.append(ops_mul)
			if ops_div is not None and current_num != 0 and current_total / current_num == x:
				successions.append(ops_div)
			if ops_pow is not None and pow(current_total, current_num) == x:
				successions.append(ops_pow)
		else: # numbers in between
			attempt = attempt_get_x(x, nums, current_total + current_num, ops_add)
			if attempt is not None:
				successions.append(attempt)
			attempt = attempt_get_x(x, nums, current_total - current_num, ops_sub)
			if attempt is not None:
				successions.append(attempt)
			attempt = attempt_get_x(x, nums, current_total * current_num, ops_mul)
			if attempt is not None:
				successions.append(attempt)
			if current_num != 0:
				attempt = attempt_get_x(x, nums, current_total / current_num, ops_div)
				if attempt is not None:
					successions.append(attempt)
			attempt = attempt_get_x(x, nums, pow(current_total, current_num), ops_pow)
			if attempt is not None:
				successions.append(attempt)

	return successions

def get_to_x(x, a, b, c, d):
	# so many loops
	successions = []
	for permutation in list(itertools.permutations([a, b, c, d])):
		attempt = attempt_get_x(x, permutation, 0, [])
		if attempt is not None:
			successions.append(attempt)

	for _ in range(0, 4): # the list looks like ass if you don't do this (flatten 4 times cause 4 numbers deep)
		successions = list(itertools.chain.from_iterable(successions))
	
	solutions = set()
	for success in successions:
		solution = ""
		for character in success:
			solution += character
		solution = solution.replace("+0","").replace("-0", "").replace("0*0", "").replace("0+", "").replace("0-", "")
		if solution[0] == "+":
			solution = solution[1:]
		solutions.add(solution)

	return sorted(solutions)

def format_train_solution(solutions):
	if len(solutions) <= 1:
		return solutions # nothing needed
	response = str(solutions[0])
	while len(solutions) > 0:
		solutions = solutions[1:]
		response += "\n" + str(solutions[0])
	return response