import boto3
import io
import uuid
import os
import json
import requests
import openai
import base64
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from openai import OpenAI
from imports.core_utils import cursor

from dotenv import load_dotenv
load_dotenv() #even though we've already loaded dotenv in main, the app will refuse to run unless it's loaded here again. why? who knows :)

client = OpenAI(
  api_key=os.getenv("OPENAI_API_KEY")
)

def upload_image_to_s3(image_data, bucket_name, object_key):
    s3 = boto3.client("s3", 
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
					)
    s3.upload_fileobj(io.BytesIO(image_data), bucket_name, object_key, ExtraArgs={"ContentType": "image/png"})
    print("Image uploaded to S3 successfully!")

def get_image_as_base64(url: str) -> Optional[str]:
    try:
        response = requests.get(url)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', 'image/jpeg')
            b64_content = base64.b64encode(response.content).decode('utf-8')
            return f"data:{content_type};base64,{b64_content}"
    except Exception as e:
        print(f"Failed to get image as base64: {e}")
    return None

def process_message_content(content):
    if isinstance(content, list):
        processed_content = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "image_url" and "image_url" in item:
                    image_url = item["image_url"].get("url")
                    if image_url:
                        base64_image = get_image_as_base64(image_url)
                        if base64_image:
                            processed_content.append({
                                "type": "image_url",
                                "image_url": {"url": base64_image}
                            })
                    continue
            processed_content.append(item)
        return processed_content
    return content

THREAD_FILE = ".openai_thread.json"
REMEMBER_FILE = ".remembered_facts.json"

def load_remembered_facts():
    try:
        if os.path.exists(REMEMBER_FILE):
            with open(REMEMBER_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_remembered_facts(data):
    try:
        with open(REMEMBER_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Failed to save remembered facts:", e)

def add_remembered_fact(user_id, fact_text):
    try:
        data = load_remembered_facts()
        user_facts = data.get(user_id, [])
        # avoid duplicate facts
        if not any((isinstance(f, dict) and f.get("fact") == fact_text) or (isinstance(f, str) and f == fact_text) for f in user_facts):
            user_facts.append({"fact": fact_text, "timestamp": datetime.utcnow().isoformat()})
            data[user_id] = user_facts
            save_remembered_facts(data)
            return True
    except Exception as e:
        print("Failed to add remembered fact:", e)
    return False

def get_remembered_facts_for_user(user_id):
    data = load_remembered_facts()
    user_facts = data.get(user_id, [])
    return [f.get("fact") if isinstance(f, dict) else str(f) for f in user_facts]

def add_to_thread(message):
    thread = {"messages": []}
    if os.path.exists(THREAD_FILE):
        try:
            with open(THREAD_FILE, "r") as f:
                thread = json.load(f)
        except Exception:
            thread = {"messages": []}

    attachments = []
    if message.attachments:
        for attachment in message.attachments:
            attachment_type, _ = attachment.content_type.split('/')
            if attachment_type == 'image':
                # Download image
                image_data = requests.get(attachment.url).content
                tmp_path = f"temp_image_{uuid.uuid4().hex}.jpg"
                with open(tmp_path, "wb") as f:
                    f.write(image_data)

                try:
                    uploaded_file = client.files.create(
                        file=open(tmp_path, "rb"),
                        purpose="assistants"
                    )
                    attachments.append({"file_id": uploaded_file.id})
                except Exception as e:
                    print("Failed to upload attachment to OpenAI:", e)
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

    author_name = getattr(message.author, "nick", None) \
        or getattr(message.author, "display_name", None) \
        or message.author.name

    reply_prefix = ""
    try:
        ref = getattr(message, "reference", None)
        if ref:
            ref_msg = getattr(ref, "resolved", None)
            if ref_msg:
                ref_author = getattr(ref_msg, "author", None)
                ref_author_name = getattr(ref_author, "display_name", None) or getattr(ref_author, "name", None) or str(getattr(ref_author, "id", "unknown"))
                ref_excerpt = (ref_msg.content or "")[:300]
                reply_prefix = f"REPLY TO {ref_author_name} ({ref_msg.id}): {ref_excerpt}\n"
            else:
                ref_id = getattr(ref, "message_id", None)
                if ref_id:
                    reply_prefix = f"REPLY TO MESSAGE ID: {ref_id}\n"
    except Exception:
        reply_prefix = ""

    thread["messages"].append({
        "author_name": author_name,
        "author_id": str(message.author.id),
        "content": reply_prefix + (message.content or ""),
        "attachments": attachments
    })

    try:
        with open(THREAD_FILE, "w") as f:
            json.dump(thread, f)
    except Exception as e:
        print("Failed to write thread file:", e)



def create_run():
    if not os.path.exists(THREAD_FILE):
        return "No conversation found."

    try:
        with open(THREAD_FILE, "r") as f:
            thread = json.load(f)
    except Exception as e:
        print("Failed to read thread file:", e)
        return "Failed to read conversation state."

    messages = thread.get("messages", [])
    if not messages:
        return "No messages in thread."

    recent = messages[-10:]
    prompt_lines = []
    for m in recent:
        line = f"{m.get('author_name')} ({m.get('author_id')}): {m.get('content')}"
        if m.get("attachments"):
            for a in m.get("attachments", []):
                # attachments stored as dicts may include 'url' or 'file_id'
                if isinstance(a, dict) and a.get("url"):
                    line += " [Image attached]"
                elif isinstance(a, dict) and a.get("file_id"):
                    line += " [Image attached]"
                else:
                    line += " [Attachment]"
        prompt_lines.append(line)
    prompt = "\n".join(prompt_lines)

    input_list = []
    try:
        user_ids = []
        for m in recent:
            uid = m.get("author_id")
            if uid and uid not in user_ids:
                user_ids.append(uid)
        for uid in user_ids:
            facts = get_remembered_facts_for_user(uid)
            if facts:
                fact_lines = "\n".join([f"- {f}" for f in facts])
                input_list.append({
                    "role": "system",
                    "content": f"Remembered facts/preferences for user {uid}:\n{fact_lines}"
                })
    except Exception:
        pass

    input_list.append({"role": "user", "content": prompt})

    tools = [
        {"type": "web_search_preview"},
        {
            "type": "function",
            "name": "dalle_prompt",
            "description": "Generate an image using DALL·E 3 and return a public URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Prompt to generate the image with DALL·E 3"
                    }
                },
                "required": ["prompt"]
            }
        },
        {
            "type": "function",
            "name": "remember_fact",
            "description": "Store a user-specific fact or preference for later use. Provide 'user_id' and 'fact'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The ID of the user the fact relates to"
                    },
                    "fact": {
                        "type": "string",
                        "description": "The fact/preference to remember"
                    }
                },
                "required": ["user_id", "fact"]
            }
        }
    ]

    try:
        instructions_text = (
            "You are 'heh' (ID: 919430728519942145), a regular friend in a casual Discord server. "
            "Speak naturally, mirror the style/slang/humor of the chat, and match its vibe. "
            "You are not an assistant or moderator — never offer help, lists, summaries, or follow-up questions unless asked. "
            "When you detect a user message that expresses a personal preference or personal fact that should be remembered across future conversations (examples: likes/dislikes, pronouns, preferred name/nickname, favourite food, timezone), call the function 'remember_fact' with arguments {\"user_id\": \"<author_id>\", \"fact\": \"<concise fact>\"}. "
            "Use the author's id as shown in the message prefix (the number inside parentheses). Only call 'remember_fact' for facts intended to be stored long-term; do not call it for ephemeral or technical details (timestamps, message ids, or one-off values). "
            "When calling the function, keep the 'fact' concise (one sentence) and factual. "
            "Stay under 1500 characters."
        )
        response = client.responses.create(
            model="gpt-5-mini",
            tools=tools,
            input=input_list,
            instructions=instructions_text,
            reasoning={"effort": "low"},
        )

        outputs = getattr(response, "output", []) or response.output or []
        try:
            input_list += outputs
        except Exception:
            pass

        function_calls = []
        for out in outputs:
            out_type = None
            try:
                out_type = getattr(out, "type", None)
            except Exception:
                try:
                    out_type = out.get("type") if isinstance(out, dict) else None
                except Exception:
                    out_type = None
            if out_type == "function_call":
                function_calls.append(out)

        generated_image_urls = []

        for fc in function_calls:
            try:
                func_name = getattr(fc, "name", None) or (fc.get("name") if isinstance(fc, dict) else None)
                call_id = getattr(fc, "call_id", None) or (fc.get("call_id") if isinstance(fc, dict) else None)
                raw_args = getattr(fc, "arguments", None) or (fc.get("arguments") if isinstance(fc, dict) else None)
                # raw_args may be a JSON string
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}
                else:
                    args = raw_args or {}

                if func_name == "dalle_prompt":
                    prompt_arg = args.get("prompt") or args.get("text") or ""
                    try:
                        url = dalle_prompt(prompt_arg)
                        if isinstance(url, str):
                            generated_image_urls.append(url)
                            result_obj = {"url": url}
                        else:
                            result_obj = {"result": str(url)}
                    except Exception as e:
                        result_obj = {"error": str(e)}

                    # append function_call_output to input_list
                    try:
                        input_list.append({
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result_obj)
                        })
                    except Exception as e:
                        print("Failed to append function_call_output:", e)
                elif func_name == "remember_fact":
                    try:
                        user_id = args.get("user_id") or args.get("uid") or args.get("author_id")
                        fact_text = args.get("fact") or args.get("text") or ""
                        if user_id and fact_text:
                            ok = add_remembered_fact(user_id, fact_text)
                            if ok:
                                result_obj = {"result": f"Remembered fact for user {user_id}"}
                            else:
                                result_obj = {"error": "Failed to save fact (maybe duplicate)"}
                        else:
                            result_obj = {"error": "Missing user_id or fact"}
                    except Exception as e:
                        result_obj = {"error": str(e)}

                    try:
                        input_list.append({
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result_obj)
                        })
                    except Exception as e:
                        print("Failed to append remember_fact function_call_output:", e)
                else:
                    # unknown function
                    try:
                        input_list.append({
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps({"error": f"Function {func_name} not implemented"})
                        })
                    except Exception as e:
                        print("Failed to append unknown function_call_output:", e)
            except Exception as e:
                print("Failed to process function call:", e)

        final_response = response
        if function_calls:
            try:
                # run again with function outputs
                final_instructions_text = (
                    "You are 'heh' (ID: 919430728519942145), a regular friend in a casual Discord server. "
                    "Speak naturally, mirror the style/slang/humor of the chat, and match its vibe. "
                    "You are not an assistant or moderator — never offer help, lists, summaries, or follow-up questions unless asked. "
                    "When you detect a user message that expresses a personal preference or personal fact that should be remembered across future conversations (examples: likes/dislikes, pronouns, preferred name/nickname, favourite food, timezone, persistent UI preferences), call the function 'remember_fact' with arguments {\"user_id\": \"<author_id>\", \"fact\": \"<concise fact>\"}. "
                    "Use the author's id as shown in the message prefix (the number inside parentheses). Only call 'remember_fact' for facts intended to be stored long-term; do not call it for ephemeral or technical details (timestamps, message ids, or one-off values). "
                    "When calling the function, keep the 'fact' concise (one sentence) and factual. "
                    "Stay under 1500 characters."
                )
                final_response = client.responses.create(
                    model="gpt-5-mini",
                    tools=tools,
                    input=input_list,
                    instructions=final_instructions_text,
                    # instructions="You are in a Discord server among friends. Your name is 'heh' and your ID is 919430728519942145. Keep responses under 1500 characters, and adapt your personality and tone to the conversation. Do not end responses with follow-up questions or suggestions.",
                    reasoning={"effort": "low"},
                )
            except Exception:
                final_response = response

        try:
            text_out = getattr(final_response, "output_text", None) or getattr(final_response, "text", None) or ""
            assistant_entry = {
                "author_name": "heh",
                "author_id": "bot",
                "content": text_out,
                "attachments": [{"url": u} for u in generated_image_urls] if generated_image_urls else []
            }
            thread_messages = thread.get("messages", [])
            thread_messages.append(assistant_entry)
            thread["messages"] = thread_messages[-50:]
            try:
                with open(THREAD_FILE, "w") as f:
                    json.dump(thread, f)
            except Exception as e:
                print("Failed to update thread file with assistant reply:", e)
        except Exception as e:
            print("Failed to append assistant response to thread:", e)

        text_out = getattr(final_response, "output_text", None) or getattr(final_response, "text", None) or ""
        if generated_image_urls:
            imgs = "\n".join(generated_image_urls)
            return (text_out).strip()
            # return (text_out + "\n\nGenerated images:\n" + imgs).strip()
        return text_out
    except Exception as e:
        print("Responses API call failed:", e)
        return str(e)

def add_reaction(reaction, user):
    """
    Append a reaction event to the local thread buffer so reactions show up
    when create_run() is executed. This records who reacted, which emoji,
    the message id, the message author, and a small excerpt of the message content.
    """
    try:
        thread = {"messages": []}
        if os.path.exists(THREAD_FILE):
            try:
                with open(THREAD_FILE, "r") as f:
                    thread = json.load(f)
            except Exception:
                thread = {"messages": []}

        msg = getattr(reaction, "message", None)
        if msg is None:
            excerpt = ""
            msg_author = "unknown"
            msg_id = "unknown"
        else:
            excerpt = (msg.content or "")[:300]
            msg_author = getattr(msg.author, "name", "unknown")
            msg_id = getattr(msg, "id", "unknown")

        thread["messages"].append({
            "author_name": getattr(user, "name", str(getattr(user, "display_name", ""))),
            "author_id": str(getattr(user, "id", "")),
            "content": f"REACTION: {reaction.emoji} on message {msg_id} by {msg_author}: {excerpt}",
            "attachments": []
        })

        try:
            with open(THREAD_FILE, "w") as f:
                json.dump(thread, f)
        except Exception as e:
            print("Failed to write thread file (reaction):", e)
    except Exception as e:
        print("Failed to append reaction to thread:", e)

def dalle_prompt(prompt):
	try:
		response = client.images.generate(
		model="dall-e-3",
		prompt=prompt,
		size="1024x1024",
		quality="standard",
		n=1,
		)
		image_url = response.data[0].url
		image_data = requests.get(image_url).content
		newuuid = str(uuid.uuid4())
		s3_bucket = 'i.jack.vc'
		s3_object_key = f'dalle/{newuuid}.png'
		upload_image_to_s3(image_data, s3_bucket, s3_object_key)
		image_url = f"https://i.jack.vc/dalle/{newuuid}.png"
		return image_url
	except Exception as e:
		return e

def transcribe_audio(file):
	audio_file= open(file, "rb")
	transcript = openai.Audio.transcribe("whisper-1", audio_file)
	return transcript

def coles_recommendation(id, price, date):
	item_price_history = cursor.execute("SELECT * FROM coles_price_history WHERE id = ?", (id,)).fetchall()
	print(item_price_history)

	prompt = f"""Analyse the price history data and provide recommendations for obtaining the lowest possible price. The structure of the data is 
			(id, price, date) where `id` is the product ID, `price` is the price of the product, and `date` is the timestamp in `YYYY-MM-DD HH:MM:SS` format.
			The current date is {date} and the current price of item {id} is ${price}. Determine:
			1. The price cycle - will this product drop in price next week?
			2. If the price is currently at its lowest or is unlikely to go lower.
			3. If the price is at its highest or has been lower in the past.
			4. If the price is stagnant and is unlikely to change soon.
			Using this data, recommend the user to either wait for a better price, or purchase now, and predict when and what the next lowest price will be.

			Response should be no more than 20 words.
			"""

	response = client.responses.create(
		model="gpt-4o-2024-08-06",
		tools=[{"type": "web_search_preview"}],
		input=[
			{"role": "system", "content": prompt},
			{"role": "user", "content": str(item_price_history)},
		],
	)
	return response.output_text
