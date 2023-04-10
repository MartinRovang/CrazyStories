import openai
from loguru import logger
import discord
from discord.ext import tasks, commands
import sys
import datetime
import sqlite3
from datetime import time
import asyncio
import numpy as np
import pytz
import os

openai.api_key = os.environ['OPENAI_API_KEY']
model_engine = "gpt-3.5-turbo"

COINS_PER_MINUTE = 3
STREAMING_MULTIPLIER = 3

norwegian_tz = pytz.timezone('Europe/Oslo')

client = commands.Bot(command_prefix='!', intents=discord.Intents.all(), case_insensitive=True)
# Connect to database
DB_NAME = '/data/cbc.db'
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY, name TEXT, cbc INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS shop
             (item_id INTEGER PRIMARY KEY, name TEXT, cost INTEGER, role_id INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_items
             (id INTEGER PRIMARY KEY, user_id INTEGER, item_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (item_id) REFERENCES shop(item_id))'''
         )
conn.commit()

TOKEN = os.environ['DISCORD_API_KEY']


# Function to get CBC for a user
def get_cbc(user_id):
    c.execute("SELECT cbc FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    if result is None:
        return 0
    else:
        return result[0]

    logger.success(f"=> Got CBC for user {user_id} ({result[0]})")


def generate_response_gpt(user_id, username):
    # get user items and get info from shop
    logger.info(f"=> Generating response for user {user_id} ({username})")
    user_items = c.execute("SELECT * FROM user_items WHERE user_id = ?", (user_id,)).fetchall()
    shop_items = c.execute("SELECT * FROM shop").fetchall()

    # get user items
    user_items_str = ""
    tmp = []
    for item in user_items:
        for shop_item in shop_items:
            if item[2] == shop_item[0]:
                if shop_item[0] in tmp:
                    continue
                tmp.append(shop_item[0])
                user_items_str += f"\n{shop_item[1]}"

    logger.info(f"=> User items: {user_items_str}")
    # generate response

    response = openai.ChatCompletion.create(model='gpt-3.5-turbo',
                                            n=1,
                                            messages=[
                                                {
                                                    "role":
                                                        "system",
                                                    "content":
                                                        f"""
                                                    As a horror and spooky story generator, I can create a story for you. The main protagonist will be named "{username}" and will have the following items in their inventory: {user_items_str}. The story title can be fun and descriptive. 

                                                    REMEBER TO REPLACE *PROTAGONIST* WITH THE "{username}" in the story.

All items mentioned in the ITEMLIST are items the protagonist has in their inventory, and if used, it should be stated that the protagonist uses the item from their inventory. The items can be sex toys, weapons, cursed items, etc. The story should include both regular and/or cursed items found during the story, and how they were found, for example: "As {username} checked the bathroom walls, they found [ :key: Key of Vengeance ]." If the protagonist dies, leave the loot section empty and include a death message in the story, indicating that all items found in the story have been lost. Relevant emoticons should always be used for the items mentioned in the story, using Discord emoticons such as :ghost:.

The story should include both regular and cursed items found during the story, and how they were found, for example: "As *PROTAGONIST* checked the bathroom walls, they found [ :key: Key of Vengeance ]." If the protagonist dies, leave the loot section empty and include a death message in the story, indicating that all items found in the story have been lost. Relevant emoticons should always be used for the items mentioned in the story, using Discord emoticons such as :ghost:.

In the story, the protagonist may also find loot drops. If there is a loot drop, include it in the story in the format: [ *DISCORD_EMOTICON* *ITEM_NAME* ]. The ITEM_NAME can be relevant to the setting or story, and the ITEM_WORTH is the amount of CBC the item is worth, between 100 and 3000. If a cursed item drops, include it in the story. If there is no loot drop, leave the section empty. If the protagonist dies, leave the loot section empty and include a death message.

The story should be kept short, under 250 words. REMEMBER TO REPLACE *PROTAGONIST* WITH THE *PROTAGONIST*'S NAME.
REMEMBER TO REPLACE *DISCORD_EMOTICON* WITH THE DISCORD EMOTICON FOR THE ITEM.
REMEMBER IF ITEMS ARE USED IN THE STORY (FROM INVENTORY), THEY SHOULD BE MENTIONED AS COMING FROM THE PROTAGONIST'S INVENTORY.
REMEMBER AND ALWAYS, WHEN ITEMS ARE USED, USE TAG EXAMPLE: [ *DISCORD_EMOTICON* *ITEM_NAME* ], example: "*PROTAGONIST* used [ :key: Key of Vengeance ], and opened the door.".

It is important to tag item usage or loot drops with the following tag example: [ *DISCORD_EMOTICON* *ITEM_NAME* ]

Please follow the template below precisely (REMEMBER TO REPLACE *PROTAGONIST* WITH THE *PROTAGONIST*'S NAME), keep story short!

EXAMPLE TITLE: The Haunted House of Insanity and Death

EXAMPLE STORY: *PROTAGONIST* had always been fascinated by abandoned houses, so when a friend told them about a spooky old mansion on the outskirts of town, they were eager to explore. As they approached the door, they noticed a faint glow emanating from a ghostly mirror hanging in the entrance hall. But they shrugged it off and continued inside.

*PROTAGONIST* was immediately struck by the eerie atmosphere of the house. They walked towards the cupboards and found a key [ :key: Key of Vengeance ] in one of them. They put it in their pocket and continued exploring. As they walked down the hallway, they heard a strange noise coming from the basement. They decided to investigate. Suddenly a demon appeared and attacked them. *PROTAGONIST* managed to kill the demon with their [ :gun: Squirt Gun ].

LOOT DROPS(MUST FOLLOW THIS EXACT TEMPLATE, VERY IMPORTANT, LEAVE EMPTY IF NO LOOT DROPS OR DEATH AND BELOW IS ONLY AN EXAMPLE):
[ :key: Key of Vengeance | 2600 ]

                                                    """
                                                },
                                                {
                                                    "role": "user",
                                                    "content": "Generate a story"
                                                },
                                                {
                                                    "role": "system",
                                                    "content": f"""TITLE: The Curse of Ravenwood Cemetery

"{username}" had always been a brave adventurer, but he had never experienced anything quite like Ravenwood Cemetery. The air was thick with the stench of death as he walked deeper into the abyss, his only source of light being the weak flame from his torch.

As he cautiously made his way through the grave markers, he heard a faint whispering that sent shivers down his spine. He drew his [ :gun: Squirt Gun ] from his belt, prepared for whatever may lurk in the shadows.

Suddenly, he heard a faint creaking sound and turned to see a ghostly figure emerging from an old mausoleum. The ghost beckoned to him and "{username}", intrigued, followed.

The ghost led him through a series of twisting corridors until they reached the inner sanctum, where "{username}" saw the source of the curse - a [ :ghost: Ghost Doll ] with a sinister aura.

He knew he had to destroy it, but the curse was too strong, and he felt his strength wane as he got closer. But he pushed through, wielding his [ :gun: Squirt Gun ] and emptied it on the cursed doll. 

The curse was lifted, and "{username}" was finally able to leave Ravenwood Cemetery. As he emerged into the sunlight, he noticed a small glimmer on the ground [ :squid: Squid Ink ].

He picked it up, feeling a sense of relief wash over him, knowing he would soon be able to afford the supplies he needed to continue his journey.

LOOT DROPS:
[ :squid: Squid Ink | 450 ]"""

                                                },
                                                {
                                                    "role": "user",
                                                    "content": "Generate a new story"
                                                },

                                            ])

    message = response.choices[0]['message']
    content = message['content']
    logger.success(f"=> Generated response for user {user_id}: {content}")
    return content


def check_if_story_made_items(content):
    # check if story made items and add to shop
    logger.info(f"=> Checking if story made items")
    items = []
    for line in content.splitlines():
        if line.startswith('['):
            item_name = line.split('|')[0].replace('[', '').strip()
            item_worth = int(line.split('|')[1].replace(']', '').replace("CBC", "").replace(",", "").strip())
            items.append((item_name, item_worth))
    logger.success(f"=> Found {len(items)} items")
    # if empty return
    if len(items) == 0:
        return None
    return items


def add_item(name, cost, role_id, item_id=None, owner='Store'):
    result = c.execute("SELECT * FROM shop WHERE item_id = ?", (item_id,)).fetchone()
    if result is None:
        c.execute("INSERT INTO shop VALUES (?, ?, ?, ?, ?)", (item_id, name, cost, role_id, owner))
        logger.success(f"=> Added item {item_id} ({name})")
    else:
        c.execute("UPDATE shop SET name = ?, cost = ?, role_id = ? WHERE item_id = ?",
                  (name, cost, role_id, item_id))
        logger.success(f"=> Updated item {item_id} ({name})")
    conn.commit()


# Function to update CBC for a user
def update_cbc(user_id, username, cbc):
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    if result is None:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (user_id, username, cbc))
    else:
        c.execute("UPDATE users SET name = ?, cbc = ? WHERE id = ?", (username, cbc, user_id))
    conn.commit()

    logger.success(f"=> Updated CBC for user {user_id} ({cbc})")


def get_shop_items():
    c.execute("SELECT * FROM shop")
    return c.fetchall()


# @client.command(name='sell', help='Sell item')
# async def sell(ctx, item_id):
#     user_id = ctx.author.id
#     cbc = get_cbc(user_id)
#     items = get_shop_items()
#     for item in items:
#         logger.info(f"=> {item[0]}, {item_id}")
#         if int(item[0]) == int(item_id):
#             update_cbc(user_id, ctx.author.name, int(cbc) + int(item[2]))
#             c.execute("DELETE FROM user_items WHERE user_id = ? AND item_id = ?", (user_id, item_id))
#             conn.commit()
#             await ctx.send(f"You sold {item[1]} for {item[2]} CBC.")
#             logger.success(f"=> Sold item {item_id} ({item[1]}) for {item[2]} CBC")
#             return
#     await ctx.send("Item not found.")


@client.command(name='buy', help='Buy item')
async def buy(ctx, item_id):
    user_id = ctx.author.id
    cbc = get_cbc(user_id)
    items = get_shop_items()
    for item in items:
        if int(item[0]) == int(item_id):
            if int(cbc) >= int(item[2]):
                update_cbc(user_id, ctx.author.name, int(cbc) - int(item[2]))
                if item[0] == 4:
                    # generate horror story
                    await ctx.send(f"Generating story...")
                    response = generate_response_gpt(user_id, str(ctx.author.name))
                    check_items = check_if_story_made_items(response)
                    if check_items is not None:
                        for item in check_items:
                            logger.info(f"=> Adding item {item[0]} ({item[1]})")
                            add_item(name=item[0],
                                     cost=int(item[1]),
                                     item_id=None,
                                     role_id=None,
                                     owner=str(ctx.author.name))
                            # add item to user
                            # get item id
                            item = c.execute("SELECT * FROM shop WHERE name = ?", (item[0],)).fetchone()
                            item_id = item[0]
                            c.execute("INSERT INTO user_items (user_id, item_id) VALUES (?, ?)",
                                      (user_id, item_id))
                    
                    response = response.replace("PROTAGONIST", str(ctx.author.name))
                    if len(response) > 2000:
                        await ctx.send(response[:2000])
                        await ctx.send(response[2000:])
                    else:
                        await ctx.send(response)
                    return

                if item[4] != "Store":
                    # remove item from player and add to new owner
                    c.execute("SELECT user_id FROM user_items WHERE item_id = ?", item_id)
                    old_owner_id = str(c.fetchone()[0]).strip()
                    logger.info(f"=> Old owner id: {old_owner_id}")
                    c.execute("SELECT * FROM users WHERE id = ?", (old_owner_id,))
                    old_owner = c.fetchone()
                    logger.info(f"=> Old owner: {old_owner}")
                    if old_owner is not None:
                        update_cbc(user_id=old_owner[0],
                                   username=old_owner[1],
                                   cbc=int(old_owner[2]) + int(item[2]))
                    c.execute("UPDATE shop SET owner = ? WHERE item_id = ?", (str(ctx.author.name), item_id))
                    c.execute("UPDATE user_items SET user_id = ? WHERE item_id = ?", (user_id, item_id))
                    conn.commit()
                    await ctx.send(f"You bought {item[1]} for {item[2]} CBC! :coin:")
                    logger.info(f"=> {ctx.author.name} bought {item[1]} ({item[2]} CBC :coin:)")
                    return

                c.execute("INSERT INTO user_items (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
                conn.commit()

                if item[3] is None:
                    await ctx.send(f"You bought {item[1]} for {item[2]} CBC! :coin:")
                    logger.info(f"=> {ctx.author.name} bought {item[1]} ({item[2]} CBC :coin:)")
                    return
                role = discord.utils.get(ctx.guild.roles, id=item[3])
                await ctx.author.add_roles(role)
                await ctx.send(f"You bought {item[1]} for {item[2]} CBC! :coin:")
                logger.info(f"=> {ctx.author.name} bought {item[1]} ({item[2]} CBC :coin:)")
            else:
                await ctx.send(f"You don't have enough CBC :coin: to buy {item[1]}!")
                logger.info(f"=> {ctx.author.name} tried to buy {item[1]} ({item[2]} CBC :coin:)")
            return
    await ctx.send(f"Item {item_id} doesn't exist!")
    logger.success(f"=> {ctx.author.name} tried to buy item {item_id}")


# Function to get user items
def get_user_items(user_id):
    c.execute("SELECT * FROM user_items WHERE user_id = ?", (user_id,))
    return c.fetchall()


@client.command(name='shop', help='Check the shop')
async def shop(ctx):
    items = get_shop_items()
    message = "Shop items:\n"
    for item in items:
        message += f"{item[0]}. {item[1]} - {item[2]} CBC :coin: Owned by: [{item[4]}]\n"
    await ctx.send(message)


@client.command(name='lb', help='Check the leaderboard')
async def lb(ctx):
    c.execute("SELECT * FROM users ORDER BY cbc DESC LIMIT 10")
    result = c.fetchall()
    message = "Leaderboard:\n"
    for user in result:
        message += f"{user[1]} - {user[2]} CBC :coin: \n"
    await ctx.send(message)
    logger.success(f"=> {ctx.author.name} checked the leaderboard")


# Event to give CBC every minute a user is in a voice chat
@tasks.loop(minutes=1)
async def give_cbc():
    for guild in client.guilds:
        for voice_channel in guild.voice_channels:
            for member in voice_channel.members:
                cbc = get_cbc(member.id)
                if member.voice.self_stream:
                    update_cbc(member.id, member.name, cbc + COINS_PER_MINUTE * STREAMING_MULTIPLIER)
                    role = discord.utils.get(guild.roles, name="Streaming Kings")
                    await member.add_roles(role, reason="Streaming voice channel")
                    logger.info(f"=> Streaming multiplier for {member.name}")
                else:
                    if "Streaming Kings" in [role.name for role in member.roles]:
                        role = discord.utils.get(guild.roles, name="Streaming Kings")
                        await member.remove_roles(role, reason="No longer streaming")
                    logger.info(f"=> Removed role for {member.name}")
                    update_cbc(member.id, member.name, cbc + COINS_PER_MINUTE)

    logger.success(f"=> Gave CBC to all users in voice channels")


# Command to check CBC for a user
@client.command(name='cbc', help='Check your CBC')
async def cbc(ctx):
    user_id = ctx.author.id
    cbc = get_cbc(user_id)
    await ctx.send(f"{ctx.author.name} has {cbc} CBC :coin:")
    logger.success(f"=> {ctx.author.name} checked their CBC ({cbc})")


@client.command(name='items', help='Check your items')
async def items(ctx):
    user_id = ctx.author.id
    items = get_user_items(user_id)
    message = "Your items:\n"
    for item in items:
        c.execute("SELECT * FROM shop WHERE item_id = ?", (item[2],))
        result = c.fetchone()
        message += f"{result[1]} \n"
    await ctx.send(message)
    logger.success(f"=> {ctx.author.name} checked their items")


# Start the client and the CBC loop
@client.event
async def on_ready():
    print(f'Logged in as {client.user.name} ({client.user.id})')
    give_cbc.start()


@client.command(name='commands', help='Check all commands')
async def commands(ctx):
    await ctx.send("Commands: \n"
                   "!cbc - Check your CBC \n"
                   "!lb - Check the leaderboard \n"
                   "!shop - Check the shop \n"
                   "!buy [item_id] - Buy an item from the shop"
                   "!items - Check your items \n")


client.run(TOKEN)
