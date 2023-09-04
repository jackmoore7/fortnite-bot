import uuid
import requests
import os
import openai
import json
import urllib
import boto3
import io

openai.organization = "org-p1aVCCHYJSv1GGzoauKukfql"
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.Model.list()

def fortnite_br_stats(username):
	url = "https://fortnite-api.com/v2/stats/br/v2"
	key = os.getenv('FNAPI_COM_KEY')
	r = requests.get(url, params={"name": username}, headers={"Authorization": key})
	return r

def fortnite_shop():
	url = "https://fortniteapi.io/v2/shop?lang=en"
	key = os.getenv('FNAPI_IO_KEY')
	r = requests.get(url, headers={"Authorization": key})
	return r.json()

def getAccountID(username):
	url = "https://fortniteapi.io/v1/lookup"
	key = os.getenv('FNAPI_IO_KEY')
	r = requests.get(url, params={"username": username}, headers={"Authorization": key})
	if r.json()['result'] != False:
		return(r.json()['account_id'])
	else:
		return "no"

def fish_loot_pool():
	url = "https://fortniteapi.io/v1/loot/fish?lang=en"
	key = os.getenv('FNAPI_IO_KEY')
	r = requests.get(url, headers={"Authorization": key})
	return r.json()

def fish_stats(username):
	url = "https://fortniteapi.io/v1/stats/fish"
	key = os.getenv('FNAPI_IO_KEY')
	accountId = getAccountID(username)
	if accountId == "no":
		return "no"
	r = requests.get(url, params={"accountId": accountId}, headers={"Authorization": key})
	if r.status_code != 200:
		print("Failed to fetch user fish data")
		return 404
	return r.json()

def fortnite_augments():
	url = "https://fortniteapi.io/v1/game/augments"
	key = os.getenv('FNAPI_IO_KEY')
	r = requests.get(url, headers={"Authorization": key})
	return r.json()

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
                    }
                },
                "required": ["prompt"],
            },
        },
    ],
    function_call="auto"
	# messages=[
	# 	{"role": "system", "content": "You are a helpful assistant."},
	# 	{"role": "user", "content": message}
	# ]
	)
	response = completion.choices[0].message
	if response.get("function_call"):
		available_functions = {
            "generate_dalle_image": dalle_prompt,
	    	"generate_dalle_variation": dalle_image_variation
        }
		function_name = response["function_call"]["name"]
		function_to_call = available_functions[function_name]
		function_args = json.loads(response["function_call"]["arguments"])
		# function_response = function_to_call(
        #     prompt=function_args.get("prompt"),
        # )
		function_response = function_to_call(**function_args)
		print(f"function response: {function_response}")
		image_data = requests.get(function_response).content
		newuuid = str(uuid.uuid4())
        # Specify your S3 bucket and object key
		s3_bucket = 'i.jack.vc'
		s3_object_key = f'dalle/{newuuid}.png'
        
        # Upload the image to S3
		upload_image_to_s3(image_data, s3_bucket, s3_object_key)
		function_response = f"https://i.jack.vc/dalle/{newuuid}.png"
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
		second_response["choices"][0]["message"]["content"] += (" " + function_response)
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
	return image_url

def dalle_image_variation(uuid):
	response = openai.Image.create_variation(
	image=open(f"{uuid}.png", "rb"),
	n=1,
	size="1024x1024"
	)
	image_url = response['data'][0]['url']
	return image_url

def transcribe_audio(file):
	audio_file= open(file, "rb")
	transcript = openai.Audio.transcribe("whisper-1", audio_file)
	return transcript

def fortnite_shop_v3():
	url = "https://fnbr.co/api/shop"
	key = os.getenv('FNBR_API_KEY')
	r = requests.get(url, headers={"x-api-key": key})
	return r.json()