import itertools
import copy
from imports.core_utils import discord, discord_client
from discord.ext.pages import Paginator, Page

import imports.api.api_openai as api_openai

async def ping(ctx):
	await ctx.respond("Ponged your ping in " + str(round(discord_client.latency * 1000)) + "ms 😳")

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
			response = get_to_x(10, a, b, c, d)
			num_of_solutions = len(response)
			if num_of_solutions == 0:
				await ctx.respond("There are no solutions for `" + str(number) + "`")
			else:
				pages = []
				response_start = "All " + str(num_of_solutions) + " solutions"
				if num_of_solutions == 1:
					response_start = "The only solution"
				elif num_of_solutions == 2:
					response_start = "Both solutions"
				formatted = check_list_length(response)
				for result_list in formatted:
					embed = discord.Embed(title="Results for train game with number " + str(number))
					embed.add_field(name=response_start, value='\n'.join(result_list))
					pages.append(Page(embeds=[embed]))
				paginator = Paginator(pages=pages)
				await paginator.respond(ctx.interaction)
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
		solution = solution.replace("+0","").replace("-0", "").replace("0*0", "").replace("0^0", "")
		if solution[0] == "+":
			solution = solution[1:]
		solutions.add(solution)

	return sorted(solutions)

def place_brackets(expression):
	return "((" + expression[0:3] + ")" + expression[3:5] + ")" + expression[5:]

def solve(num1, op, num2):
	result = 0
	if op == "+":
		result = float(num1) + float(num2)
	elif op == "-":
		result = float(num1) - float(num2)
	elif op == "*":
		result = float(num1) * float(num2)
	elif op == "/":
		result = float(num1) / float(num2)
	elif op == "^":
		result = pow(float(num1), float(num2))
	
	if result == int(result):
		return int(result)
	else:
		return "{:.3f}".format(result) # 3 decimal points

def breakdown_expression(sol0):
	# ((0+9)+0)+1 -> (9+0)+1 -> 9+1 -> 10
	if len(sol0) != 11:
		print("Somehow got a solution the wrong length (" + str(len(sol0)) + "): " + sol0)
		return sol0
	
	so_far = solve(sol0[2], sol0[3], sol0[4])
	sol1 = "(" + str(so_far) + sol0[6:]

	so_far = solve(so_far, sol0[6], sol0[7])
	sol2 = str(so_far) + sol0[9:]

	so_far = solve(so_far, sol0[9], sol0[10])
	sol3 = str(so_far)

	return sol0 + " -> " + sol1 + " -> " + sol2 + " -> " + sol3

def format_train_solution(solutions):
    formatted = []
    for sol in solutions:
        sol = place_brackets(sol)
        sol = str(breakdown_expression(sol))  # only cast here so python knows its a string even though it always is
        sol = sol.replace("*", "\*")
        formatted.append(sol)
    return formatted

def check_list_length(solutions):
    formatted_list = format_train_solution(solutions)
    total_length = sum(len(solution) for solution in formatted_list)
    
    if total_length > 1024:
        num_items = len(formatted_list)
        third = num_items // 3
        first_third = formatted_list[:third]
        second_third = formatted_list[third:2*third]
        third_third = formatted_list[2*third:]
        return [first_third, second_third, third_third]
    else:
        return [formatted_list]