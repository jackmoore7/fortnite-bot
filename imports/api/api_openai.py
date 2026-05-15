import base64
import io
import json
import os
import uuid
from datetime import datetime
from typing import Literal, Optional
from zoneinfo import ZoneInfo

import boto3
import openai
import requests
from openai import OpenAI
from pydantic import BaseModel, Field

from imports.core_utils import cursor

MAX_CONVERSATION_MESSAGES = 40

from dotenv import load_dotenv

load_dotenv() #even though we've already loaded dotenv in main, the app will refuse to run unless it's loaded here again. why? who knows :)

client = OpenAI(
  api_key=os.getenv("OPENAI_API_KEY")
)

def get_conversation_id():
    result = cursor.execute("SELECT conversation_id FROM conversation WHERE id = 1").fetchone()
    return result[0]

def set_conversation_id(new_id):
    cursor.execute("UPDATE conversation SET conversation_id = ? WHERE id = 1", (new_id,))

def count_conversation_messages():
    """
    Count the number of 'message' type items in the current conversation.
    Returns the count of user/assistant messages only (ignoring function calls, reasoning, etc).
    """
    try:
        conv_id = get_conversation_id()
        items_response = client.conversations.items.list(conv_id, limit=100)
        items = getattr(items_response, "data", []) or []
        
        message_count = sum(1 for item in items if getattr(item, "type", None) == "message")
        return message_count
    except Exception as e:
        print(f"Failed to count conversation messages: {e}")
        return 0

def prune_old_messages():
    """
    Remove the oldest 'message' type items from the conversation if it exceeds MAX_CONVERSATION_MESSAGES.
    Preserves all other item types (function calls, reasoning, etc).
    """
    try:
        conv_id = get_conversation_id()
        items_response = client.conversations.items.list(conv_id, limit=100, order="asc")
        items = getattr(items_response, "data", []) or []
        
        message_items = [item for item in items if getattr(item, "type", None) == "message"]
        
        if len(message_items) > MAX_CONVERSATION_MESSAGES:
            items_to_delete = len(message_items) - MAX_CONVERSATION_MESSAGES
            print(f"DEBUG: Pruning {items_to_delete} oldest messages (total: {len(message_items)} -> {MAX_CONVERSATION_MESSAGES})")
            
            for item in message_items[:items_to_delete]:
                item_id = getattr(item, "id", None)
                if item_id:
                    try:
                        client.conversations.items.delete(conversation_id=conv_id, item_id=item_id)
                        print(f"DEBUG: Deleted message item {item_id}")
                    except Exception as e:
                        print(f"Failed to delete message item {item_id}: {e}")
    except Exception as e:
        print(f"Failed to prune old messages: {e}")

def upload_image_to_s3(image_data, bucket_name, object_key):
    s3 = boto3.client("s3", 
                endpoint_url=os.getenv("R2_ENDPOINT_URL"),
                aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
                region_name="auto",
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



def add_to_thread(message):
    author_name = getattr(message.author, "nick", None) \
        or getattr(message.author, "display_name", None) \
        or message.author.name

    reply_excerpt = ""
    ref_author_name = ""
    is_reply = False
    try:
        ref = getattr(message, "reference", None)
        if ref:
            ref_msg = getattr(ref, "resolved", None)
            if ref_msg:
                reply_excerpt = (ref_msg.content or "")[:300]
                ref_author = getattr(ref_msg, "author", None)
                ref_author_name = getattr(ref_author, "display_name", None) or getattr(ref_author, "name", None) or str(getattr(ref_author, "id", "unknown"))
                is_reply = True
    except Exception:
        pass

    if is_reply:
        full_text = f"{author_name} replied to {ref_author_name}'s message `{reply_excerpt}`: {message.content or ''}"
    else:
        full_text = f"{author_name} said: {message.content or ''}"
    content_list = [{"type": "input_text", "text": full_text}]

    if message.attachments:
        for attachment in message.attachments:
            attachment_type, _ = attachment.content_type.split('/')
            if attachment_type == 'image':
                image_data = requests.get(attachment.url).content
                filename = f"{message.id}_{attachment.filename}"
                filepath = os.path.join("temp_images", filename)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                print(f"Image uploaded and saved: {filepath}")
                from PIL import Image
                img = Image.open(filepath)
                print(img.size, os.path.getsize(filepath))
                b64_content = base64.b64encode(image_data).decode('utf-8')
                data_url = f"data:{attachment.content_type};base64,{b64_content}"
                content_list.append({"type": "input_image", "image_url": data_url, "detail": "high"})

    import re
    url_pattern = r'https?://[^\s]+\.(?:png|jpg|jpeg|gif|webp)(?:\?[^\s]*)?'
    urls = re.findall(url_pattern, full_text)
    for url in urls:
        try:
            image_data = requests.get(url).content
            import uuid
            filename = f"url_{uuid.uuid4().hex}.png"
            filepath = os.path.join("temp_images", filename)
            with open(filepath, "wb") as f:
                f.write(image_data)
            print(f"Image from URL uploaded and saved: {filepath}")
            content_type = 'image/jpeg'
            b64_content = base64.b64encode(image_data).decode('utf-8')
            data_url = f"data:{content_type};base64,{b64_content}"
            content_list.append({"type": "input_image", "image_url": data_url, "detail": "high"})
        except Exception as e:
            print(f"Failed to download image from URL {url}: {e}")

    message_dict = {
        "type": "message",
        "role": "user",
        "content": content_list
    }

    try:
        client.conversations.items.create(get_conversation_id(), items=[message_dict])
        prune_old_messages()
    except Exception as e:
        print("Failed to add message to conversation:", e)



def create_run():
    print("DEBUG: Starting create_run")
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
        }
    ,

    {

        "type": "function",

        "name": "get_wordle_answer",

        "description": "Get the Wordle solution for a specific date.",

        "parameters": {

            "type": "object",

            "properties": {

                "date": {

                    "type": "string",

                    "description": "The date in YYYY-MM-DD format"

                }

            },

            "required": ["date"]

        }

    }

]

    try:
        print("DEBUG: Creating initial response")
        instructions_text = (
            "You are 'heh' (ID: 919430728519942145), a regular friend in a Discord server. "
            "Speak casually as you would in a chat room, mirroring the slang/style/humour of the chat and match its vibe. "
            "You are not an assistant, bot, or moderator. Never offer help, lists, summaries, or follow-up questions unless asked. "
            "The current datetime (AEST/AEDT) is " + datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d %H:%M:%S") + ". "
            "You can get Wordle solutions using the get_wordle_answer tool when someone asks for the Wordle answer. "
            "Keep responses as short as possible."
        )
        response = client.responses.create(
            model="gpt-4.1",
            conversation=get_conversation_id(),
            input=[],
            tools=tools,
            instructions=instructions_text
        )
        print("DEBUG: Initial response created successfully")

        outputs = getattr(response, "output", []) or response.output or []
        print(f"DEBUG: Outputs from initial response: {outputs}")

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
        print(f"DEBUG: Function calls found: {len(function_calls)}")

        generated_image_urls = []
        wordle_solutions = []
        last_call_id = None

        for fc in function_calls:
            print(f"DEBUG: Processing function call: {fc}")
            try:
                fc_call_id = getattr(fc, "call_id", None) or (fc.get("call_id") if isinstance(fc, dict) else None)
                func_name = getattr(fc, "name", None) or (fc.get("name") if isinstance(fc, dict) else None)
                raw_args = getattr(fc, "arguments", None) or (fc.get("arguments") if isinstance(fc, dict) else None)
                print(f"DEBUG: Function name: {func_name}, call_id: {fc_call_id}, args: {raw_args}")
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}
                else:
                    args = raw_args or {}

                if func_name == "dalle_prompt":
                    prompt_arg = args.get("prompt") or args.get("text") or ""
                    print(f"DEBUG: Calling dalle_prompt with prompt: {prompt_arg}")
                    try:
                        url = dalle_prompt(prompt_arg)
                        print(f"DEBUG: dalle_prompt returned: {url}")
                        if isinstance(url, str):
                            generated_image_urls.append(url)
                            if fc_call_id:
                                last_call_id = fc_call_id
                        print(f"DEBUG: Generated URLs so far: {generated_image_urls}")
                    except Exception as e:
                        print("Failed to generate image:", e)

                elif func_name == "get_wordle_answer":

                    date = args.get("date")

                    solution = get_wordle_answer(date)

                    if solution:

                        wordle_solutions.append(solution)

                        if fc_call_id:

                            last_call_id = fc_call_id

            except Exception as e:
                print("Failed to process function call:", e)

        print(f"DEBUG: Generated image URLs: {generated_image_urls}")
        input_messages = []
        print(f"DEBUG: Initial input_messages: {input_messages}")
        if generated_image_urls:
            try:
                output_item = {
                    "type": "function_call_output",
                    "call_id": last_call_id,
                    "output": json.dumps({"generated_images": generated_image_urls})
                }
                input_messages.append(output_item)
                print(f"DEBUG: Appended function_call_output: {output_item}")
            except Exception as e:
                print("Failed to prepare function_call_output for follow-up response:", e)

        if wordle_solutions:

            try:

                output_item = {

                    "type": "function_call_output",

                    "call_id": last_call_id,

                    "output": json.dumps({"wordle_solutions": wordle_solutions})

                }

                input_messages.append(output_item)

                print(f"DEBUG: Appended function_call_output for wordle: {output_item}")

            except Exception as e:

                print("Failed to prepare function_call_output for wordle:", e)

        final_response = response
        if function_calls:
            print("DEBUG: Making second responses.create call")
            try:
                final_instructions_text = (
                    "You are 'heh' (ID: 919430728519942145), a regular friend in a Discord server. "
                    "Speak casually as you would in a chat room, mirroring the slang/style/humour of the chat and match its vibe. "
                    "You are not an assistant, bot, or moderator. Never offer help, lists, summaries, or follow-up questions unless asked. "
                    "The current datetime (AEST/AEDT) is " + datetime.now(ZoneInfo("Australia/Sydney")).strftime("%Y-%m-%d %H:%M:%S") + ". "
                    "You can get Wordle solutions using the get_wordle_answer tool when someone asks for the Wordle answer. "
                    "Keep responses as short as possible."
                )
                final_response = client.responses.create(
                    model="gpt-4.1",
                    conversation=get_conversation_id(),
                    tools=tools,
                    instructions=final_instructions_text,
                    input=input_messages if 'input_messages' in locals() else [],
                )
                print("DEBUG: Second response created successfully")
            except Exception as e:
                print(f"DEBUG: Second response failed, falling back to initial response. Error: {e}")
                final_response = response
        print(f"DEBUG: Final response object: {final_response}")
        output_text = getattr(final_response, "output_text", None)
        print(f"DEBUG: output_text from final_response: {output_text}")
        if isinstance(output_text, str):
            text_out = output_text
        elif output_text is None:
            text_out = ""
        else:
            try:
                if hasattr(output_text, "text"):
                    text_out = getattr(output_text, "text") or ""
                elif hasattr(output_text, "content"):
                    text_out = getattr(output_text, "content") or ""
                else:
                    text_out = str(output_text)
            except Exception:
                text_out = ""
        print(f"DEBUG: text_out: '{text_out}'")
        if generated_image_urls:
            if text_out.strip():
                print("DEBUG: Returning text_out.strip()")
                return text_out.strip()
            else:
                print("DEBUG: Returning joined URLs")
                return "\n".join(generated_image_urls)
        print("DEBUG: Returning text_out")
        return text_out
    except Exception as e:
        print("Responses API call failed:", e)
        return str(e)

def add_edit_to_thread(before, after):
    """
    Add an edit message to the conversation.
    """
    try:
        author_name = getattr(after.author, "nick", None) \
            or getattr(after.author, "display_name", None) \
            or after.author.name
        edit_content = f"{author_name} edited their message: '{before.content}' -> '{after.content}'"
        content_list = [{"type": "input_text", "text": edit_content}]

        if after.attachments:
            for attachment in after.attachments:
                attachment_type, _ = attachment.content_type.split('/')
                if attachment_type == 'image':
                    image_data = requests.get(attachment.url).content
                    filename = f"{after.id}_{attachment.filename}"
                    filepath = os.path.join("temp_images", filename)
                    with open(filepath, "wb") as f:
                        f.write(image_data)
                    print(f"Image uploaded in edit and saved: {filepath}")
                    b64_content = base64.b64encode(image_data).decode('utf-8')
                    data_url = f"data:{attachment.content_type};base64,{b64_content}"
                    content_list.append({"type": "input_image", "image_url": data_url, "detail": "high"})

        import re
        url_pattern = r'https?://[^\s]+\.(?:png|jpg|jpeg|gif|webp)(?:\?[^\s]*)?'
        urls = re.findall(url_pattern, after.content)
        for url in urls:
            try:
                image_data = requests.get(url).content
                filename = f"url_edit_{uuid.uuid4().hex}.png"
                filepath = os.path.join("temp_images", filename)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                print(f"Image from URL in edit uploaded and saved: {filepath}")
                content_type = 'image/jpeg'
                b64_content = base64.b64encode(image_data).decode('utf-8')
                data_url = f"data:{content_type};base64,{b64_content}"
                content_list.append({"type": "input_image", "image_url": data_url, "detail": "high"})
            except Exception as e:
                print(f"Failed to download image from URL {url}: {e}")

        if after.embeds:
            for embed in after.embeds:
                if embed.image:
                    url = embed.image.url
                    data_url = get_image_as_base64(url)
                    if data_url:
                        content_list.append({"type": "input_image", "image_url": data_url, "detail": "high"})
                        try:
                            image_data = requests.get(url).content
                            filename = f"embed_{after.id}_{uuid.uuid4().hex}.png"
                            filepath = os.path.join("temp_images", filename)
                            with open(filepath, "wb") as f:
                                f.write(image_data)
                            print(f"Image from embed uploaded and saved: {filepath}")
                        except Exception as e:
                            print(f"Failed to save image from embed {url}: {e}")
                if embed.thumbnail:
                    url = embed.thumbnail.url
                    data_url = get_image_as_base64(url)
                    if data_url:
                        content_list.append({"type": "input_image", "image_url": data_url, "detail": "high"})
                        try:
                            image_data = requests.get(url).content
                            filename = f"embed_thumb_{after.id}_{uuid.uuid4().hex}.png"
                            filepath = os.path.join("temp_images", filename)
                            with open(filepath, "wb") as f:
                                f.write(image_data)
                            print(f"Thumbnail from embed uploaded and saved: {filepath}")
                        except Exception as e:
                            print(f"Failed to save thumbnail from embed {url}: {e}")

        message_dict = {
            "type": "message",
            "role": "user",
            "content": content_list
        }
        client.conversations.items.create(get_conversation_id(), items=[message_dict])
        prune_old_messages()
    except Exception as e:
        print("Failed to add edit to conversation:", e)

def add_reaction(reaction, user):
    """
    Add a reaction message to the conversation.
    """
    try:
        author_name = getattr(user, "nick", None) \
            or getattr(user, "display_name", None) \
            or user.name
        msg = getattr(reaction, "message", None)
        if msg is None:
            excerpt = ""
        else:
            excerpt = (msg.content or "")[:300]

        reaction_content = f"{author_name} reacted {reaction.emoji} to {excerpt}"
        message_dict = {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": reaction_content}]
        }
        client.conversations.items.create(get_conversation_id(), items=[message_dict])
        prune_old_messages()
    except Exception as e:
        print("Failed to add reaction to conversation:", e)

def dalle_prompt(prompt):
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openrouter_base = "https://openrouter.ai/api/v1"

    def try_download(url):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.content
        except Exception:
            return None
        return None

    def extract_url_from_entry(entry):
        if not entry:
            return None
        if isinstance(entry, dict):
            img_obj = entry.get("image_url") or {}
            if isinstance(img_obj, dict):
                return img_obj.get("url")
            if isinstance(img_obj, str):
                return img_obj
        return None

    if not openrouter_key:
        raise Exception("OPENROUTER_API_KEY not configured; no fallback configured.")

    or_client = OpenAI(base_url=openrouter_base, api_key=openrouter_key)
    try:
        completion = or_client.chat.completions.create(
            model="openai/gpt-5-image-mini",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
    except Exception as e:
        raise Exception(f"OpenRouter request failed: {e}")

    first_choice = None
    if getattr(completion, "choices", None):
        first_choice = completion.choices[0]
    elif isinstance(completion, dict) and "choices" in completion:
        first_choice = completion["choices"][0]

    if not first_choice:
        raise Exception("No choice in OpenRouter/GPT-5-image-mini response")

    if isinstance(first_choice, dict):
        msg = first_choice.get("message") or {}
    else:
        msg = getattr(first_choice, "message", {}) or {}

    images_list = msg.get("images") if isinstance(msg, dict) else getattr(msg, "images", None)
    image_bytes = None
    image_url = None

    if images_list:
        for entry in images_list:
            url = extract_url_from_entry(entry)
            if not url:
                continue
            if url.startswith("data:") and ";base64," in url:
                try:
                    b64 = url.split(";base64,")[-1]
                    image_bytes = base64.b64decode(b64)
                    break
                except Exception:
                    continue
            if url.startswith("http://") or url.startswith("https://"):
                data = try_download(url)
                if data:
                    image_bytes = data
                    break
                else:
                    image_url = url
                    continue

    if not image_bytes and not image_url:
        raw_content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
        if isinstance(raw_content, list):
            for block in raw_content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "image_url":
                    url = extract_url_from_entry(block)
                    if url:
                        if url.startswith("data:") and ";base64," in url:
                            try:
                                b64 = url.split(";base64,")[-1]
                                image_bytes = base64.b64decode(b64)
                                break
                            except Exception:
                                continue
                        if url.startswith("http://") or url.startswith("https://"):
                            data = try_download(url)
                            if data:
                                image_bytes = data
                                break
                            else:
                                image_url = url
                                continue
                if block.get("type") == "text":
                    txt = block.get("text", "") or ""
                    if "data:" in txt and ";base64," in txt:
                        try:
                            b64 = txt.split(";base64,")[-1]
                            image_bytes = base64.b64decode(b64)
                            break
                        except Exception:
                            pass
                    s = txt.strip()
                    if s.startswith("http://") or s.startswith("https://"):
                        data = try_download(s)
                        if data:
                            image_bytes = data
                            break
                        else:
                            image_url = s
                            continue
        elif isinstance(raw_content, str):
            s = raw_content.strip()
            if s.startswith("http://") or s.startswith("https://"):
                data = try_download(s)
                if data:
                    image_bytes = data
                else:
                    image_url = s
            elif "data:" in s and ";base64," in s:
                try:
                    b64 = s.split(";base64,")[-1]
                    image_bytes = base64.b64decode(b64)
                except Exception:
                    pass

    if image_bytes:
        newuuid = str(uuid.uuid4())
        s3_bucket = "i-jack-vc"
        s3_object_key = f"dalle/{newuuid}.png"
        upload_image_to_s3(image_bytes, s3_bucket, s3_object_key)
        return f"https://i.jack.vc/dalle/{newuuid}.png"
    if image_url:
        return image_url

    raise Exception("OpenRouter/GPT-5-image-mini did not return an image")

def get_wordle_answer(date: str) -> str:
    try:
        url = f"https://www.nytimes.com/svc/wordle/v2/{date}.json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("solution", "")
        else:
            return ""
    except Exception as e:
        print(f"Failed to get Wordle answer: {e}")
        return ""

def transcribe_audio(file):
	audio_file= open(file, "rb")
	transcript = openai.Audio.transcribe("whisper-1", audio_file)
	return transcript

class PriceRecommendation(BaseModel):
    current_status: Literal["Peak", "Mid-Range", "Floor", "Stagnant"]
    recommendation: Literal["Buy Now", "Wait"]
    predicted_price: float = Field(description="The next likely lowest price point")
    expected_days_until_drop: int = Field(description="Days until the next discount")
    logic: str = Field(description="Max 15 words explaining the cycle")

def coles_recommendation(item_id, price, date):
    history = cursor.execute(
        "SELECT price, date FROM coles_price_history WHERE id = ? ORDER BY date DESC LIMIT 20", 
        (item_id,)
    ).fetchall()

    prompt = f"""
    Analyze Coles price history. Current item {item_id} is ${price} on {date}.
    History: {history}
    
    Identify the High-Low cycle. If the price is currently at the 'Full Price' 
    seen in history, recommend 'Wait'. If it matches the historical 'Floor', recommend 'Buy Now'.
    """

    response = client.beta.chat.completions.parse(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a grocery price bot. Minimize spend."},
            {"role": "user", "content": prompt},
        ],
        response_format=PriceRecommendation,
    )
    
    return response.choices[0].message.parsed