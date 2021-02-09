import discord
from discord import Activity, ActivityType
import requests  # dependency
import json
import sys
import logging
from PIL import Image
import requests
import numpy
from io import BytesIO
from discord.ext import commands

import time

import sqlite3
from sqlite3 import Error

# import base64

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)


def close_connection(conn):
    if conn:
        conn.close()


def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)
        exit()


DB_PATH = r"guilds.db"
conn = create_connection(DB_PATH)
sql_create_guilds_table = """ CREATE TABLE IF NOT EXISTS guilds (
                                        id integer PRIMARY KEY,
                                        name text NOT NULL,
                                        levenshtein integer,
                                        language text,
                                        prefix text,
                                        tts integer
                                    ); """


if conn:
    create_table(conn, sql_create_guilds_table)
    close_connection(conn)
else:
    print("BIG FAIL WHILE CONNECTING TO DB.\nCRASHING")
    exit()

# print(mydb)

API_ENDPOINT = 'https://discord.com/api/v6'

bot = commands.Bot(command_prefix='$')
bot.remove_command('help')


def get_content(file):
    # Read file content
    try:
        file = open(file, "r")
        s = file.read()
        file.close()
    except Exception as error:
        return ""
    return s


token_dev = get_content("token_dev")
token = get_content("token")


def pseudo_from_id(id):
    """
    Gets all information about a user
    """
    r = requests.get(f"{API_ENDPOINT}/users/{id}",
                     headers={
                         'Authorization': f'Bot {token}',
                         'Content-Type': 'application/x-www-form-urlencoded',
                     }).json()

    avatar_url = r['avatar']

    return (
        r['username'],
        f"https://cdn.discordapp.com/avatars/{id}/{avatar_url}.png?size=128"
    )


dev_pseudo, dev_avatar_url = pseudo_from_id(289145021922279425)
print((dev_pseudo, dev_avatar_url))


def levenshtein(token1, token2):
    distances = numpy.zeros((len(token1) + 1, len(token2) + 1))

    for t1 in range(len(token1) + 1):
        distances[t1][0] = t1

    for t2 in range(len(token2) + 1):
        distances[0][t2] = t2

    # a = 0
    # b = 0
    # c = 0

    for t1 in range(1, len(token1) + 1):
        for t2 in range(1, len(token2) + 1):
            if (token1[t1-1] == token2[t2-1]):
                distances[t1][t2] = distances[t1 - 1][t2 - 1]
            else:
                a = distances[t1][t2 - 1]
                b = distances[t1 - 1][t2]
                c = distances[t1 - 1][t2 - 1]

                if (a <= b and a <= c):
                    distances[t1][t2] = a + 1
                elif (b <= a and b <= c):
                    distances[t1][t2] = b + 1
                else:
                    distances[t1][t2] = c + 1

    return distances[len(token1)][len(token2)]


# def printDistances(distances, token1Length, token2Length):
#     for t1 in range(token1Length + 1):
#         for t2 in range(token2Length + 1):
#             print(int(distances[t1][t2]), end=" ")
#         print()


def db_new(guild_id, guild_name):
    print(f"Addind {guild_name} as {guild_id}")
    conn = create_connection(DB_PATH)
    cur = conn.cursor()
    sql = f'''INSERT INTO guilds (id, name, levenshtein, language, prefix, tts) VALUES (?, ?, ?, ?, ?, ?)'''
    args = (guild_id, guild_name, True, "en", "$", False)
    cur.execute(sql, args)

    conn.commit()
    close_connection(conn)


def db_exec(sql, args=None):
    conn = create_connection(DB_PATH)
    cur = conn.cursor()

    if args:
        exec = cur.execute(sql, args).fetchall()
    else:
        exec = cur.execute(sql).fetchall()
    conn.commit()
    close_connection(conn)

    return exec


def db_exists(guild_id):
    sql = f'''SELECT * FROM guilds ORDER BY id'''

    db = db_exec(sql)

    for row in db:
        if guild_id == row[0]:
            return row

    return None


def extract_message(c):
    """
    Exacts all informations about the message sent to activate a command
    """

    message = c.message

    id = message.id

    chan = message.channel

    chan_id = chan.id
    chan_name = chan.name
    chan_position = chan.position
    chan_nsfw = chan.nsfw
    chan_categry_id = chan.category_id
    chan_message_type = chan.type

    auth = message.author

    author_id = auth.id
    author_name = auth.name
    author_discriminator = auth.discriminator
    author_isbot = auth.bot
    author_nick = auth.nick

    guild = auth.guild

    guild_id = guild.id
    guild_name = guild.name
    guild_shard = guild.shard_id
    guild_chunked = guild.chunked
    guild_membercount = guild.member_count

    flags = message.flags

    dict = {}
    dict["id"] = id

    dict["chan_id"] = chan_id
    dict["chan_name"] = chan_name
    dict["chan_pos"] = chan_position
    dict["chan_nsfw"] = chan_nsfw
    dict["chan_cat"] = chan_categry_id
    dict["chan_type"] = chan_message_type

    dict["auth_id"] = author_id
    dict["auth_name"] = author_name
    dict["auth_disc"] = author_discriminator
    dict["auth_bot"] = author_isbot
    dict["auth_nick"] = author_nick

    dict["guild_id"] = guild_id
    dict["guild_name"] = guild_name
    dict["guild_shard"] = guild_shard
    dict["guild_chunked"] = guild_chunked
    dict["guild_mbcount"] = guild_membercount

    dict["flags"] = flags

    return dict


async def best_name(name, context):
    if name.isdigit():
        return pseudo_from_id(name)
    if name[0] == '.' or name[0] == ':':
        return name[1:], None

    min = -1
    sql = f'SELECT levenshtein FROM guilds WHERE id={context.guild.id}'
    DO_LEVENSTEIN = db_exec(sql)[0][0]

    if DO_LEVENSTEIN == 0 or context.guild.member_count > 50:
        return name, None

    try:
        members = await context.guild.fetch_members(limit=None).flatten()
        print("worked")
    except:
        print("Error => fetch_members failed")
        return name, None  # In case fetch failed

    li = list()

    for i in range(len(members)):
        mem_user = members[i].nick
        if not mem_user:
            mem_user = members[i].name

        # print(mem_user.lower() + ' - ' + name.lower())
        namelen = len(name)
        mem = mem_user[:namelen]
        if len(name) < len(mem_user):
            li.append(100)
        else:
            li.append(levenshtein(mem_user.lower(), name.lower()))
        if min == -1 or li[i] <= li[min]:
            min = i

    # print(li)

    username = members[min].nick
    if not username:
        username = members[min].name

    if li[min] >= 2:
        return name, None

    _, url = pseudo_from_id(members[min].id)
    return username, url


async def parse_args(context, *args):
    username = context.author.name + \
        "#" + context.author.discriminator
    print(f'{time.time()}: {username} entered \'fake\'')

    if not db_exists(context.guild.id):
        await bot.change_presence(activity=Activity(name=f"{len(bot.guilds)} servers",
                                                    type=ActivityType.watching))
        db_new(context.guild.id, context.guild.name)

    await context.message.delete()
    print("Didn't delete (debug purpose)")

    name = None
    msg = None
    url = None

    if "http" in args[-1]:
        url = args[-1]
    if len(args) >= 2:
        last = len(args)
        if url:
            last -= 1

        msg = ' '.join(args[1:last])
        if url and not args[0].isdigit():
            name, _ = await best_name(args[0], context)
        else:
            name, url = await best_name(args[0], context)

    print((name, msg, url))
    print
    return (name, msg, url)
    # print(extract_message(context))


@ bot.event
async def on_ready():
    """
    Sets the bots current activity
    """

    await bot.wait_until_ready()
    await bot.change_presence(activity=Activity(name=f"{len(bot.guilds)} servers",
                                                type=ActivityType.watching))

    print(f'Currently at {len(bot.guilds)} servers!')
    print('Servers connected to:')
    print('')

    for guild in bot.guilds:
        if not db_exists(guild.id):
            db_new(guild.id, guild.name)

    print('----------------------------------------------')
    print()


@ bot.command(name='help')
async def help(context):
    """
    The help embed
    """
    username = context.message.author.name + \
        "#" + context.message.author.discriminator
    print(f'{time.time()}: {username} entered \'help\'')

    embed = discord.Embed(title="The FAKER", colour=discord.Colour(
        0x95255c), url="https://patreon.com/erwanvivien",
        # description="Ever wanted to impersonate your friends ?\n" +
        # "This is how :")
    )

    embed.set_thumbnail(
        url="https://www.foreignaffairs.com/sites/default/files/anchor.gif")
    # embed.set_author(name="FAKER bot", url="https://discordapp.com",
    #                  icon_url="https://www.internetandtechnologylaw.com/files/2019/06/iStock-872962368-chat-bots.jpg")
    embed.set_footer(text=f"@Patreon : erwanvivien",
                     icon_url=dev_avatar_url)

    embed.add_field(name="The main functionnality",
                    value="$fake ``\"DISCORD_ID|NAME\"`` ``MESSAGE`` ``[IMAGE_URL]`` with \n" +
                    " - ``DISCORD_ID``'s name and ``DISCORD_ID``'s image OR\n" +
                    " - ``NAME``'s name and default image\n" +
                    " - ``IMAGE_URL`` is not mandatory, it sets the bot image to said url",
                    inline=False)
    embed.add_field(name="Smart search",
                    value="$set lev ``on|off``",
                    inline=True)
    embed.add_field(name="Language",
                    value="$set lang ``language``",
                    inline=True)

    message = await context.send(embed=embed)

    await message.add_reaction(emoji='❎')

    def check(reaction, user):
        return user.id != bot.user.id and reaction.emoji in ['❎']

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=15, check=check)
    except:
        return

    if reaction.emoji == '❎':
        await message.delete()
        return


@ bot.command(name='fake')
async def fake(context, *args):
    """
    Usurpates a user
    """
    if len(args) <= 1:
        await help(context)
        return

    web = None
    webs = await context.channel.webhooks()
    for w in webs:
        if w.user.id == bot.user.id:
            web = w
            break
        # alread = alread or w.user.id == bot.user.id

    if not web:
        web = await context.message.channel.create_webhook(name='Webhook for spam')

    name, msg, url = await parse_args(context, *args)
    await web.send(content=msg, username=name, avatar_url=url)

    print()


@ bot.command(name='reset')
async def reset(context):
    """
    Resets the bots name and image
    """
    username = context.message.author.name + \
        "#" + context.message.author.discriminator
    print(f'{time.time()}: {username} entered \'reset\'')

    # await context.message.guild.me.edit(nick=None, avatar=None)
    await bot.user.edit(avatar=None, username="The FAKER", nick=None)
    await context.message.delete()

    embed = discord.Embed(title="Reset Done !",
                          description="The name and image has been reseted",
                          colour=discord.Colour(0x95255c))
    await context.send(embed=embed)


@ bot.command(name='settings')
async def settings(context, setting=None, arg=None):
    await set_(context, setting, arg)


@ bot.command(name='set')
async def set_(context, setting=None, arg=None):
    conn = create_connection(DB_PATH)
    cur = conn.cursor()

    username = context.author.name + \
        "#" + context.author.discriminator
    print(f'{time.time()}: {username} entered \'set\'')

    sql = f'''SELECT * FROM guilds ORDER BY id'''
    db = db_exec(sql)[0]

    if not setting:
        # print(db)
        embed = discord.Embed(title="Current settings",
                              colour=discord.Colour(0x95255c))
        embed.add_field(name="PROPERTY",
                        value="Smart search\n\n" +
                        "Language\n\n" +
                        "TTS",
                        inline=True)
        embed.add_field(name="VALUE",
                        value=("✅" if db[2] != 0 else "❎") + "\n\n" +
                        "🇬🇧\n\n" +
                        ("✅" if db[5] != 0 else "❎"),

                        inline=True)
        await context.send(embed=embed)
        return

    if arg:
        arg = arg.lower()
    setting = setting.lower()

    sql = None
    if "lev" in setting:
        sql = f'''UPDATE guilds SET levenshtein={1 if arg and arg != "off" else 0} WHERE id={context.guild.id}'''
        embed = discord.Embed(title="Updated levenshtein property",
                              description="The levenshtein search is now turned " +
                              ("on" if arg and arg != "off" else "off"),
                              colour=discord.Colour(0x95255c))

    elif "lang" in setting:
        sql = f'''UPDATE guilds SET language={arg if arg else "en"} WHERE id={context.guild.id}'''
        embed = discord.Embed(title="Updated language property",
                              description="Now the language is " +
                              (arg if arg else "en"),
                              colour=discord.Colour(0x95255c))

    elif "tts" in setting and (context.message.author.id == 289145021922279425 or context.message.author.guild_permissions.administrator):
        sql = f'''UPDATE guilds SET tts={1 if arg and arg != "off" else 0} WHERE id={context.guild.id}'''

        embed = discord.Embed(title="Updated TTS property",
                              description="Now the TSS is " +
                              ("on" if arg and arg != "off" else "off"),
                              colour=discord.Colour(0x95255c))
    elif "tts" in setting and not context.message.author.guild_permissions.administrator:
        close_connection(conn)
        embed = discord.Embed(title="You need to be admin to change this property",
                              description="Ask an admin to change this :)",
                              colour=discord.Colour(0x95255c))
        await context.send(embed=embed)
        return
    # elif "pref" in setting:
    #     sql = f'''UPDATE guilds SET prefix={arg if arg else "$"} WHERE id={context.guild.id}'''
    #     embed = discord.Embed(title="Updated prefix property",
    #                           description=f"The new prefix is ``" +
    #                           (arg if arg else "$") + "``",
    #                           colour=discord.Colour(0x95255c))

    if not sql:
        close_connection(conn)
        embed = discord.Embed(title="Property not found",
                              description="Please check ``help`` for more informations",
                              colour=discord.Colour(0x95255c))
        await context.send(embed=embed)
        return

    await context.send(embed=embed)

    db_exec(sql)


@ bot.command(name='members')
async def members(context):
    """
    prints all members
    """
    username = context.message.author.name + \
        "#" + context.message.author.discriminator
    print(f'{time.time()}: {username} entered \'members\'')

    # members = await context.guild.fetch_members(limit=None).flatten()
    members = await context.message.guild.fetch_members(limit=None).flatten()

    str = ""
    for name in members:
        username = name.nick
        if not username:
            username = name.name
        # print(username)
        str += username + "\n"

    await context.send(str)


@bot.event
async def on_reaction_add(reaction, user):
    if user.id != bot.user.id:
        print(reaction.emoji + ' from ' + user.name)


@ bot.command(name='clean')
async def clean(context):
    await deleteall(context)
    return


@ bot.command(name='deleteall')
async def deleteall(context):
    if not (context.author.id == 289145021922279425 or context.author.guild_permissions.administrator):
        close_connection(conn)
        embed = discord.Embed(title="You need to be admin to change this property",
                              description="Ask an admin to change this :)",
                              colour=discord.Colour(0x95255c))
        await context.send(embed=embed)
        return

    embed = discord.Embed(title="YOU ARE GOING TO DO THE UN-UNDOABLE",
                          description="Are you really sure you want to delete all informations about your server on the database ?\n" +
                          "This will lead to the loss of every settings, webhooks created on your server.\n" +
                          "You won't be able to go to the previous state after this command.",
                          colour=discord.Colour(0x95255c))
    message = await context.send(embed=embed)
    await message.add_reaction(emoji='✅')
    await message.add_reaction(emoji='🛑')

    def check(reaction, user):
        return user.id != bot.user.id and reaction.emoji in ['✅', '🛑']

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=15, check=check)
    except:
        return

    if reaction.emoji == '🛑':
        await message.delete()
        return
    elif reaction.emoji != '✅':
        return

    nb_delete = 0
    webhooks = await context.guild.webhooks()
    for webhook in webhooks:
        if webhook.user.id == bot.user.id:
            await webhook.delete()
            nb_delete += 1

    sql = f'DELETE FROM guilds WHERE id={context.guild.id};'
    db_exec(sql)

    embed = discord.Embed(title="YOU DID THE UN-UNDOABLE",
                          description=f"{nb_delete} webhooks have been deleted.\n" +
                          "The server has been removed from the database.",
                          colour=discord.Colour(0x95255c))
    message = await context.send(embed=embed)


@ bot.command(name='faketts')
async def faketts(context, *args):
    """
    Usurpates a user
    """
    if len(args) <= 1:
        await help(context)
        return

    sql = f'SELECT * FROM guilds WHERE id={context.guild.id}'
    params = db_exec(sql)[0]
    # print(params)

    if params[5] == 0:
        await fake(context, *args)
        return

    web = None
    webs = await context.channel.webhooks()
    for w in webs:
        if w.user.id == bot.user.id:
            web = w
            break
        # alread = alread or w.user.id == bot.user.id

    if not web:
        web = await context.message.channel.create_webhook(name='Webhook for spam')

    name, msg, url = await parse_args(context, *args)
    await web.send(content=msg, username=name, avatar_url=url, tts=True)

    # print(web.url)

    # response = requests.get(url)
    # await bot.user.edit(avatar=BytesIO(response.content).read(), username=name)

    # await context.send(msg)
    print()


@ bot.command(name='faketss')
async def faketss(context, *args):
    await faketts(context, *args)


@ bot.command(name='test')
async def test(context):
    print()

bot.run(token)
