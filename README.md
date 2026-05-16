[![Python 3.13.5](https://img.shields.io/badge/python-3.13.5-blue.svg)](https://www.python.org/downloads/release/python-3135/)

A bot I made for my friends and I. Feel free to message me if you have questions :)

# Important info
This has kind of turned into an amalgamation of a bunch of different projects into one repo, so cloning this repo will almost certainly not be beneficial for you. 
If you find a feature you might find helpful, feel free to copy that part of code and add it to your own implementation.

# Features

## Fortnite

### Updates
An internal task that checks the current version of the Fortnite manifest, and is configured to post in a specific channel when there's an update. 
A **launcherAppClient2** token is needed for this function. Fortunately, the credentials you need to generate it is the same for everyone. You can grab them from [MixV2's Epic Research repo](https://github.com/MixV2/EpicResearch/blob/master/docs/auth/auth_clients.md).

### Server status
An internal task that checks the current status of Fortnite via Epic's Lightswitch service, configured to post in a specific channel when the status changes.
A **fortnitePCGameClient** token is needed for this function. Again, you can get this from [MixV2's Epic Research repo](https://github.com/MixV2/EpicResearch/blob/master/docs/auth/auth_clients.md).

## Sun protection
![NVIDIA_Share_gy3j9SL3QM](https://github.com/jackmoore7/fortnite-bot/assets/53585628/09e97b68-c0df-4e8b-b0f9-948a6da5e36a)

Posts the UV forecast and protection window in the morning, and updates every minute throughout the day. Includes a ping if the forecast was incorrect.
Uses data from [ARPANSA](https://www.arpansa.gov.au/).

## Coles
![image](https://github.com/jackmoore7/fortnite-bot/assets/53585628/9094d1fa-df53-4092-9790-ff84c72478b1)

This is also its own repo, but this one will almost certainly be more up to date. The plan is to make this a web app one day.

### Product tracking
Get updates when a product you're tracking changes. This can include price, promotional status, and availability. 

### Search
Search for an item. Uses a Discord embed with pagination.

### Product tracking
Get updates when a product you're tracking changes. This can include price, promotional status, and availability.

### Search
Search for an item. Uses a Discord embed with pagination. Doesn't work very well because the way Lego's search function works is absolutely wack.

## Miscellaneous

### Train Game
Find all solutions to the 'train game'. Given a four digit number (0000-9999), get to the number 10 using addition, subtraction, multiplication, division, and exponentiation.
