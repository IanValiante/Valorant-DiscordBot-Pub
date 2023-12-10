import asyncio
import discord
import motor.motor_asyncio
from discord.ext import commands
import requests 
import json
from datetime import datetime
import pytz
import schedule


# Initialize the bot

intents = discord.Intents.all()
intents.typing = False
intents.presences = False
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

#Initialize the API

api_key = "####################################"


#Initialize MongoDB

url = "mongodb+srv://group:group@groupproject.nt55qnv.mongodb.net/?retryWrites=true&w=majority"
port = 27017
database_name = "test_data"
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(url)
db = mongo_client["test_data"]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    asyncio.create_task(schedule_task())
    schedule.every().sunday.at("20:00").do(lambda: asyncio.create_task(send_scheduled_message()))

#Commands

@bot.command()
async def hello(ctx):
    await ctx.send("Hello, I am your Discord bot!")

#Add to db



#Get Stats from the database

@bot.command()
async def getOldStats(ctx, username):
    # Retrieve data from the MongoDB collection
    collection = db["tests"]
    query = {"username" : username}
    stats_cursor = collection.find(query)

    # Convert the cursor to a list
    stats_list = await stats_cursor.to_list(length=100)
    stats = stats_list[0]
    print(stats)
    # Send each document as a separate message
    await ctx.send(f"__{username}'s Stats from {stats['date']} and older__ \n**Most recent game** \n   When: {stats['date']} at {stats['time']}EST \n**Total** \n  Kills: {stats['total_kills']}, Deaths: {stats['total_deaths']} \n**Average** \n   Kills: {stats['average_kills']}, Deaths: {stats['average_deaths']}") 
#Put Stats into DB
async def setOldStats(username,kills,deaths,assists,total_kills,average_kills,total_deaths,average_deaths,date,time):
    # Insert data into the MongoDB collection
    new_vals = {
    "$set": {
        "kills" : kills,
        "deaths" : deaths,
        "assists" : assists,
        "username": username,
        "total_kills": total_kills,
        "average_kills": average_kills,
        "total_deaths": total_deaths,
        "average_deaths": average_deaths,
        "date": date,
        "time": time
        }
    }
    collection = db["tests"]
    try:
        query = {"username" : username}
        await collection.update_one(query,new_vals)
    except:
        await collection.insert_one(new_vals)
    
@bot.command()
async def getStats(ctx,*,username):
    #Splitting name and tag
    tag = ""
    name, tag = username.split("#", 1)
    # Replace spaces with '%'
    name = name.replace(' ', '%')

    mode = "competitive"
    headers = {
    "Authorization": api_key,
}   
    #Endpoint URL
    try:
        url = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/na/{name}/{tag}?mode={mode}"
        #Get json response from API
        response = requests.get(url=url, headers=headers)
        json_data = response.json()
        # Extract and return the list of matches
        matches = json_data['data']
    except:
        await ctx.send("User does not exist or has not played any matches")
    

    # Sort the matches by the 'started_at' field in descending order
    sorted_matches = sorted(matches, key=lambda x: x['meta']['started_at'], reverse=True)

    #loop over the sorted matches to extract information
    count = 0
    total_kills = 0
    average_kills = 0
    total_deaths = 0
    average_deaths = 0
    for match in sorted_matches:
        # Extract specific data
        count += 1
        match_id = match['meta']['id']
        if(count ==1):
            #Get Start time of most recent match
            start_time = match['meta']['started_at']
            #Split date and time 
            date,time = start_time.split("T",1)
            #Date is returned Y/M/D we want M/D/Y
            year = date[0:4]
            month = date[5:7]
            day = date[8:10]
            #Set to M/D/Y
            date = month+"/"+day+"/"+year
            utc_timestamp_str = start_time
            utc_timestamp = datetime.strptime(utc_timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            # Define the UTC timezone
            utc_timezone = pytz.timezone("UTC")
            # Localize the UTC timestamp
            utc_timestamp = utc_timezone.localize(utc_timestamp)
            # Define the Eastern Standard Time (EST) timezone
            est_timezone = pytz.timezone("America/New_York")
            # Convert the timestamp to EST
            est_timestamp = utc_timestamp.astimezone(est_timezone)
            est_timestamp_str = est_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
            #Extract time from date string
            time = est_timestamp_str[11:16]
            OGkills = match['stats']['kills']
            OGdeaths = match['stats']['deaths']
            OGassists = match['stats']['assists']
        kills = match['stats']['kills']
        deaths = match['stats']['deaths']
        #Get total and average kills/deaths
        total_kills += kills 
        average_kills = round(total_kills/count,2)
        total_deaths += deaths
        average_deaths = round(total_deaths/count,2)
        #Get headshot %
        headshots = match['stats']['shots']['head']
        total_shots = match['stats']['shots']['body'] + match['stats']['shots']['leg'] + headshots
        headshot_perc = round((headshots/total_shots)*100,2)
        # Send the latest match data to the Discord channel
    name = name.replace('%',' ')
    await ctx.send(f"__{name}'s Stats__ \n**Most recent game** \n   When: {date} at {time}EST, Kills: {OGkills}, Deaths: {OGdeaths}, Assists: {OGassists} \n**Total** \n  Kills: {total_kills}, Deaths: {total_deaths} \n**Average** \n   Kills: {average_kills}, Deaths: {average_deaths}, Headshot Percentage: {headshot_perc}%\n **These averages are based off a total of {count} games.") 
    #await setOldStats(username,kills,deaths,OGassists,total_kills,average_kills,total_deaths,average_deaths,date,time)

required_reaction_count = 6
async def scrimSchedule(ctx,message):
    sent_message = await ctx.send(message)
    await sent_message.add_reaction('👍')
    await sent_message.add_reaction('👎')
    message_id = sent_message.id
async def on_reaction_add(ctx,reaction,message_id):
    # Check if the reaction is on the target message
    if reaction.message.id == message_id:
        # Check if the reaction count meets the requirement
        if reaction.count >= required_reaction_count:
            ctx.send(f"There will be practice on {await ctx.fetch_message(int(message_id))}")
    
async def send_scheduled_message():
    channel_id = 1092177598227947602
    channel = bot.get_channel(channel_id)

    if channel:
         await scrimSchedule(channel,message="Monday")
         await scrimSchedule(channel,message="Tuesday")
         await scrimSchedule(channel,message="Wednesday")
         await scrimSchedule(channel,message="Thursday")
         await scrimSchedule(channel,message="Friday")
         await scrimSchedule(channel,message="Saturday")
         await scrimSchedule(channel,message="Sunday")
async def schedule_task():
    while True:
        await asyncio.sleep(1)
        schedule.run_pending()

    
# Run the bot
bot.run("#############################")
