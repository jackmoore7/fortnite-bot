import boto3
import io
import uuid
import os
import requests
import openai
import base64
from pydantic import BaseModel
from typing import Optional

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

def openai_chat(messages, user_info=None, channel_info=None):
	try:
		system_context = {
			"user": {
				"name": user_info.get("name", "Unknown"),
				"roles": user_info.get("roles", []),
				"joined_at": user_info.get("joined_at", "Unknown"),
			},
			"channel": {
				"name": channel_info.get("name", "Unknown"),
				"type": channel_info.get("type", "Unknown"),
				"topic": channel_info.get("topic", ""),
			}
		}

		messages[0]["content"] = f"""Rules and Context:
- You are a helpful Discord assistant
- Current context:
  - User: {system_context['user']['name']} (Roles: {', '.join(system_context['user']['roles'])})
  - Channel: #{system_context['channel']['name']} ({system_context['channel']['type']})
  - Topic: {system_context['channel']['topic']}
Important Rules:
- Keep responses under 1500 characters
- Respond naturally to the message content
- Consider user roles and channel context
- Maintain a helpful and friendly tone"""

		processed_messages = []
		for msg in messages:
			processed_msg = msg.copy()
			processed_msg["content"] = process_message_content(msg["content"])
			processed_messages.append(processed_msg)

		completion = client.chat.completions.create(
			model="gpt-4o-mini",
			messages=processed_messages,
			temperature=0.7,
			max_tokens=800,
		)
		return completion.choices[0].message.content
	except Exception as e:
		return f"I encountered an error: {str(e)}. Please try again or rephrase your message."
	
def add_to_thread(role, content):
	client.beta.threads.messages.create("thread_D2OVE4uaACCXPqf31zoXdpM1",role=role,content=content)

def create_run():
	thread_id = client.beta.threads.retrieve("thread_D2OVE4uaACCXPqf31zoXdpM1").id
	run = client.beta.threads.runs.create_and_poll(
    	thread_id=thread_id,
    	assistant_id=client.beta.assistants.retrieve("asst_ex4zlCf9tXa7dav0YvD2eCjm").id
	)
	if run.status == 'completed': 
		messages = client.beta.threads.messages.list(
			thread_id=thread_id
		)
		return messages.data[0].content[0].text.value
	else:
		print(run.status)

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

	class PriceRecommendation(BaseModel):
		recommendation: str


	completion = client.beta.chat.completions.parse(
	model="gpt-4o-2024-08-06",
	messages=[
		{"role": "system", "content": prompt},
		{"role": "user", "content": str(item_price_history)},
	],
	response_format=PriceRecommendation,
	)
	return completion.choices[0].message.parsed.recommendation