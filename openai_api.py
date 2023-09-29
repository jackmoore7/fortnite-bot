import json
import boto3
import io
import uuid
import openai
import os
import requests

openai.organization = "org-p1aVCCHYJSv1GGzoauKukfql"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.Model.list()

from third_party_api import *

def upload_image_to_s3(image_data, bucket_name, object_key):
    s3 = boto3.client("s3", 
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
					)
    s3.upload_fileobj(io.BytesIO(image_data), bucket_name, object_key, ExtraArgs={"ContentType": "image/png"})
    print("Image uploaded to S3 successfully!")

def chatgpt_query(messages_list):
	print(f"messages list length: {len(messages_list)}")
	while len(messages_list) > 5:
		messages_list.pop(1)
	completion = openai.ChatCompletion.create(
	model="gpt-3.5-turbo",
	messages=messages_list,
	functions = [
        {
            "name": "generate_dalle_image",
            "description": "Generate an image based on a textual description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The textual description of the image.",
                    },
					"url": {
						"type": "string",
						"descrription": "The URL of the image to be included in followup message."
					}
                },
                "required": ["prompt"],
            },
        },
		# {
        #     "name": "get_fortnite_image",
        #     "description": "Get the image of a Fortnite cosmetic by name. User must specify they are searching for an item from Fortnite. If return is null, say the item doesn't exist.",
        #     "parameters": {
        #         "type": "object",
        #         "properties": {
        #             "name": {
        #                 "type": "string",
        #                 "description": "The name of the Fortnite cosmetic.",
        #             },
		# 			"url": {
		# 				"type": "string",
		# 				"description": "The URL of the image to be included in followup message."
		# 			}
        #         },
        #         "required": ["name"],
        #     },
        # },
    ],
    function_call="auto"
	)
	response = completion.choices[0].message
	if response.get("function_call"):
		available_functions = {
            "generate_dalle_image": dalle_prompt,
	    	# "get_fortnite_image": get_fortnite_image1
        }
		function_name = response["function_call"]["name"]
		function_to_call = available_functions[function_name]
		function_args = json.loads(response["function_call"]["arguments"])
		function_response = function_to_call(*list(function_args.values()))
		print(f"function args: {function_args}")
		if function_response:
			print(f"function response: {function_response}")
			messages_list.append(response)
			messages_list.append(
            	{
					"role": "function",
					"name": function_name,
					"content": function_response,
            	}
        	)
			second_response = openai.ChatCompletion.create(
				model="gpt-3.5-turbo-0613",
				messages=messages_list,
			)
			print(f"second response: {second_response}")
			second_response["choices"][0]["message"]["content"]
			return second_response
	print(f"completion: {completion}")
	return completion

def dalle_prompt(prompt):
	response = openai.Image.create(
	prompt=prompt,
	n=1,
	size="1024x1024"
	)
	image_url = response['data'][0]['url']
	image_data = requests.get(image_url).content
	newuuid = str(uuid.uuid4())
	s3_bucket = 'i.jack.vc'
	s3_object_key = f'dalle/{newuuid}.png'
	upload_image_to_s3(image_data, s3_bucket, s3_object_key)
	image_url = f"https://i.jack.vc/dalle/{newuuid}.png"
	return image_url

def dalle_image_variation(uuid):
	response = openai.Image.create_variation(
	image=open(f"{uuid}.png", "rb"),
	n=1,
	size="1024x1024"
	)
	image_url = response['data'][0]['url']
	return image_url

def get_fortnite_image1(name):
	response = fortnite_images(name)
	if response:
		return response
	else:
		return "This item doesn't exist"

def transcribe_audio(file):
	audio_file= open(file, "rb")
	transcript = openai.Audio.transcribe("whisper-1", audio_file)
	return transcript