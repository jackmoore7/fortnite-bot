from imports.api.api_openai import client, get_conversation_id, set_conversation_id

async def clear_conversation(ctx):
	await ctx.defer()
	try:
		current_id = get_conversation_id()
		items_response = client.conversations.items.list(current_id)
		items = getattr(items_response, "data", []) or []
		deleted_count = 0
		for item in items:
			if getattr(item, "type", None) == "message":
				try:
					client.conversations.items.delete(conversation_id=current_id, item_id=item.id)
					deleted_count += 1
				except Exception as e:
					print(f"Failed to delete item {item.id}: {e}")
		await ctx.respond(f"Cleared {deleted_count} messages from the conversation.")
	except Exception as e:
		print(f"Failed to clear conversation: {e}")
		await ctx.respond("Failed to clear the conversation.")

async def new_conversation(ctx):
	await ctx.defer()
	try:
		current_id = get_conversation_id()
		client.conversations.delete(current_id)
		new_conversation = client.conversations.create(metadata={"topic": "discord_bot"})
		new_id = getattr(new_conversation, "id", None)
		if new_id:
			set_conversation_id(new_id)
			await ctx.respond("Deleted the old conversation and started a new one.")
		else:
			await ctx.respond("Failed to create new conversation.")
	except Exception as e:
		print(f"Failed to create new conversation: {e}")
		await ctx.respond("Failed to create new conversation.")

async def list_conversation(ctx):
	await ctx.defer()
	try:
		current_id = get_conversation_id()
		items_response = client.conversations.items.list(current_id, limit=20)
		items = getattr(items_response, "data", []) or []

		if not items:
			await ctx.respond("No messages in the conversation.")
			return

		conversation_parts = []
		for item in reversed(items):
			item_type = getattr(item, "type", None)
			id = getattr(item, "id", "unknown")
			status = getattr(item, "status", "unknown")

			if item_type == "message":
				role = getattr(item, "role", "unknown")
				content = getattr(item, "content", [])

				content_parts = []
				for c in content:
					c_type = getattr(c, "type", None)
					if c_type == "input_text":
						text = getattr(c, "text", "").replace("\"", "\\\"")
						content_parts.append(f"InputTextContent(text=\"{text}\", type='input_text')")
					elif c_type == "input_image":
						detail = getattr(c, "detail", "auto")
						file_id = getattr(c, "file_id", None)
						image_url = getattr(c, "image_url", None)
						content_parts.append(f"InputImageContent(detail='{detail}', file_id={file_id}, image_url={image_url}, type='input_image')")
					elif c_type == "output_text":
						text = getattr(c, "text", "").replace("\"", "\\\"")
						annotations = getattr(c, "annotations", [])
						logprobs = getattr(c, "logprobs", [])
						content_parts.append(f"OutputTextContent(annotations={annotations}, text=\"{text}\", type='output_text', logprobs={logprobs})")

				content_str = ", ".join(content_parts)
				conversation_parts.append(f"Message(id='{id}', content=[{content_str}], role='{role}', status='{status}', type='{item_type}')")

			elif item_type == "function_call_output":
				call_id = getattr(item, "call_id", None)
				output = getattr(item, "output", "").replace("\"", "\\\"")
				conversation_parts.append(f"ResponseFunctionToolCallOutputItem(id='{id}', call_id='{call_id}', output='{output}', type='{item_type}', status='{status}')")

			elif item_type == "function_call":
				call_id = getattr(item, "call_id", None)
				name = getattr(item, "name", None)
				arguments = getattr(item, "arguments", "").replace("\"", "\\\"")
				conversation_parts.append(f"ResponseFunctionToolCallItem(arguments='{arguments}', call_id='{call_id}', name='{name}', type='{item_type}', id='{id}', status='{status}')")

			elif item_type == "reasoning":
				summary = getattr(item, "summary", [])
				content = getattr(item, "content", None)
				encrypted_content = getattr(item, "encrypted_content", None)
				conversation_parts.append(f"ResponseReasoningItem(id='{id}', summary={summary}, type='{item_type}', content={content}, encrypted_content={encrypted_content}, status={status})")

		full_response = "[" + ", ".join(conversation_parts) + "]"

		if len(full_response) > 2000:
			chunks = [full_response[i:i+2000] for i in range(0, len(full_response), 2000)]
			for chunk in chunks:
				await ctx.respond(chunk)
		else:
			await ctx.respond(full_response)

	except Exception as e:
		print(f"Failed to list conversation: {e}")
		await ctx.respond("Failed to list the conversation.")