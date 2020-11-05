#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################
#........../\./\...___......|\.|..../...\.........#
#........./..|..\/\.|.|_|._.|.\|....|.c.|.........#
#......../....../--\|.|.|.|i|..|....\.../.........#
#        Mathtin (c)                              #
###################################################
#   Author: Daniel [Mathtin] Shiko                #
#   Copyright (c) 2020 <wdaniil@mail.ru>          #
#   This file is released under the MIT license.  #
###################################################

__author__ = 'Mathtin'

import logging
import bot
import db
import db.queries as q

from util import *

log = logging.getLogger('control')

############################
# Control command Handlers #
############################

@cmdcoro
async def ping(client: bot.Overlord, msg: discord.Message):
    await msg.channel.send("pong")

@cmdcoro
async def calc_channel_stats(client: bot.Overlord, msg: discord.Message, channel: str):
    # Extract id from channel mention format
    try:
        channel_id = int(channel[2:-1])
    except ValueError:
        await msg.channel.send("Mention channel properly!")
        return
    
    # Resolve channel
    channel = client.get_channel(channel_id)
    if channel is None:
        await msg.channel.send("Unknown channel")
        return
    elif not is_text_channel(channel):
        await msg.channel.send("Not a text channel")
        return
    
    new_msg_event = client.event_type("new_message")

    # Tranaction begins
    async with client.sync():

        # Drop full channel message history
        log.warn(f'Dropping #{channel.name}({channel.id}) history')
        await msg.channel.send(f'Attention: dropping {channel.mention} history')
        client.db.query(db.MessageEvent).filter_by(channel_id=channel.id).delete()

        _user_cache = {}

        # Load all messages
        log.info(f'Loading #{channel.name}({channel.id}) history')
        async for message in channel.history(limit=None,oldest_first=True):

            # Skip bot messages
            if message.author.id in client.bot_members:
                continue

            # Resolve user
            if message.author.id not in _user_cache:
                user = q.get_user_by_did(client.db, message.author.id)
                if user is None and client.config["user.left.keep"]:
                    user = client.db.add(db.User, user_row(message.author))
                _user_cache[message.author.id] = user
            else:
                user = _user_cache[message.author.id]

            # Skip users not in db
            if user is None:
                continue

            # Insert new message event
            row = new_message_to_row(user, message, new_msg_event)
            client.db.add(db.MessageEvent(**row))

        # Calc stats
        #log.info(f'Calculating #{channel.name}({channel.id}) statistics')
        #await msg.channel.send(f'Calculating #{channel.name}({channel.id}) statistics')

        # Commit changes
        log.info(f'Commiting changes for #{channel.name}({channel.id})')
        await msg.channel.send(f'Commiting changes for #{channel.name}({channel.id})')
        client.db.commit()

        log.info(f'Done')
        await msg.channel.send(f'Done')


