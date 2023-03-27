A bot I made for my friends and I. Feel free to message me if you have questions :)

# ‼
Important: This repo doesn't work out of the box! There are a *lot* of enviroment variables and the database isn't in this repo. You'll need to update these to your specs. 

## Features
### Fortnite updates
An internal task that checks the current version of the Fortnite manifest, and is configured to post in a specific channel when there's an update. 
A **launcherAppClient2** token is needed for this function. Fortunately, the credentials you need to generate it is the same for everyone. You can grab them from [MixV2's Epic Research repo](https://github.com/MixV2/EpicResearch/blob/master/docs/auth/auth_clients.md).

### Fortnite status
An internal task that checks the current status of Fortnite via Epic's Lightswitch service, configured to post in a specific channel when the status changes.
A **fortnitePCGameClient** token is needed for this function. Again, you can get this from [MixV2's Epic Research repo](https://github.com/MixV2/EpicResearch/blob/master/docs/auth/auth_clients.md).

### Daily shop
An internal task that checks whether there are new items in the shop every 5 minutes. It only posts items that weren't in the shop yesterday. 
I used [FortniteAPI.io](https://fortniteapi.io)'s API for this feature. 

### Shop offers
An internal task that checks whether there are new offers ($) in the shop every 30 minutes. 
Posts the name, price, expiration date and image. Fortunately, this doesn't require any authentication. 