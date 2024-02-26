![NVIDIA_Share_gy3j9SL3QM](https://github.com/jackmoore7/fortnite-bot/assets/53585628/39b09910-4498-43bb-aaba-503b0890c2ac)[![Python 3.9.2](https://img.shields.io/badge/python-3.9.2-blue.svg)](https://www.python.org/downloads/release/python-392/)

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

### Daily shop
An internal task that checks whether there are new items in the shop every 5 minutes. It only posts items that weren't in the shop yesterday. 
I used [FortniteAPI.io](https://fortniteapi.io)'s API for this feature. 

### Shop offers
An internal task that checks whether there are new offers ($) in the shop every 30 minutes. 
Posts the name, price, expiration date and image. Fortunately, this doesn't require any authentication. 

## Automatic Windscribe ephemeral port forwarding
Unfortunately Windscribe doesn't offer a public API to add/change an ephemeral peer port for your account so I had to use **Selenium** (stop crying it'll be okay).
It works by getting a new ephemeral peer port, using Transmission's RPC to change the client's peer port, and using **subprocess** to send a reboot command to a Docker container running Transmission (so the new port takes effect).
Very hacky but it works :)

## Sun protection
![NVIDIA_Share_gy3j9SL3QM](https://github.com/jackmoore7/fortnite-bot/assets/53585628/09e97b68-c0df-4e8b-b0f9-948a6da5e36a)
Posts the UV forecast and protection window in the morning, and updates every minute throughout the day. Includes a ping if the forecast was incorrect.
Uses data from [ARPANSA](https://www.arpansa.gov.au/)

## Coles
This is also its own repo, but this one will almost certainly be more up to date. The plan is to make this a web app one day.

### Product tracking
Get updates when a product you're tracking changes. This can include price, promotional status, and availability. 

### Search
Search for an item. Uses a Discord embed with pagination.

## Lego
![Discord_UO0FnT8ldL](https://github.com/jackmoore7/fortnite-bot/assets/53585628/b2ebce6c-57d2-4a40-a328-cef73df12976)
Mostly just made this for a friend who likes Lego and wanted to be the first to know when an out of stock item would be available again. Plus, I wanted to see if I could tackle the absolute mess of GraphQL they use (it's so scary).

### Product tracking
Get updates when a product you're tracking changes. This can include price, promotional status, and availability.

### Search
Search for an item. Uses a Discord embed with pagination. Doesn't work very well because the way Lego's search function works is absolutely wack.
