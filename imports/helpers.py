import pytz
import re

from datetime import datetime as dt
from time import mktime

nice_try = "nice try bozo"
removed = "Removed ✅"
added = "Added ✅"
time_format = '%Y-%m-%dT%H:%M:%S.%fZ'
timezone = pytz.timezone('Australia/Sydney')

def timestampify(string):
	date_time_obj = dt.strptime(string, '%Y-%m-%dT%H:%M:%S%z')
	struct_time = date_time_obj.timetuple()
	return f"<t:{int(mktime(struct_time))}:R>"

def timestampify_z(string):
	date_time_obj = dt.strptime(string, time_format)
	struct_time = date_time_obj.timetuple()
	return f"<t:{int(mktime(struct_time))}:R>"

def embed_tweets(message):
    url_regex = re.compile(r'https?:\/\/(?:www\.)?(twitter|x)\.com\/(?:#!\/)?(\w+)\/status(?:es)?\/(\d+)')
    replacement_regex = r'https://fxtwitter.com/\2/status/\3'
    match = url_regex.search(message.content)
    if match:
        url = match.group(0)
        modified_url = re.sub(url_regex, replacement_regex, url)
        modified_text = message.content.replace(url, modified_url)
        return modified_text

def percentage_change(old, new):
    try:
        change = new - old
        relative_change = change / abs(old)
        percentage_change = relative_change * 100
        formatted_percentage_change = f"{percentage_change:.2f}%"
        if percentage_change > 0:
            formatted_percentage_change = "+" + formatted_percentage_change
        return formatted_percentage_change
    except ZeroDivisionError:
        return "inf%"