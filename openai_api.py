import json
import boto3
import io
import uuid
import os
import requests
import openai
from openai import OpenAI
from third_party_api import *

client = OpenAI(
  organization='org-p1aVCCHYJSv1GGzoauKukfql',
  project='proj_7Y6EqNlguorsqDiEGOxBbagM',
)

def upload_image_to_s3(image_data, bucket_name, object_key):
    s3 = boto3.client("s3", 
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
					)
    s3.upload_fileobj(io.BytesIO(image_data), bucket_name, object_key, ExtraArgs={"ContentType": "image/png"})
    print("Image uploaded to S3 successfully!")

def openai_chat(messages):

	completion = client.chat.completions.create(
	model="gpt-4o",
	messages=messages
	)
	return completion.choices[0].message.content

def dalle_prompt(prompt):
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

def transcribe_audio(file):
	audio_file= open(file, "rb")
	transcript = openai.Audio.transcribe("whisper-1", audio_file)
	return transcript