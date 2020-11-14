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

from sqlalchemy.orm import query
import bot
import db
import db.queries as q
import db.converters as conv

from util import *
import util.resources as res

log = logging.getLogger('control')

############################
# Control command Handlers #
############################

@cmdcoro
async def ping(client: bot.Overlord, msg: discord.Message):
    await msg.channel.send(res.get_string("messages.pong"))

@cmdcoro
async def calc_channel_stats(client: bot.Overlord, msg: discord.Message, channel: str):
    # Extract id from channel mention format
    try:
        channel_id = int(channel[2:-1])
    except ValueError:
        await msg.channel.send(res.get_string("messages.invalid_channel_mention"))
        return
    
    # Resolve channel
    channel = client.get_channel(channel_id)
    if channel is None:
        await msg.channel.send(res.get_string("messages.unknown_channel"))
        return
    elif not is_text_channel(channel):
        await msg.channel.send(res.get_string("messages.invalid_channel_type_text"))
        return

    # Tranaction begins
    async with client.sync():

        # Drop full channel message history
        log.warn(f'Dropping #{channel.name}({channel.id}) history')
        answer = res.get_string("messages.channel_history_drop").format(channel.mention)
        await msg.channel.send(answer)
        client.db.query(db.MessageEvent).filter_by(channel_id=channel.id).delete()
        client.db.commit()

        _user_cache = {}

        # Load all messages
        log.info(f'Loading #{channel.name}({channel.id}) history')
        async for message in channel.history(limit=None,oldest_first=True):

            # Skip bot messages
            if message.author.bot:
                continue

            # Resolve user
            if message.author.id not in _user_cache:
                user = q.get_user_by_did(client.db, message.author.id)
                if user is None and client.config["user.leave.keep"]:
                    user = client.db.add(db.User, conv.user_row(message.author))
                _user_cache[message.author.id] = user
            else:
                user = _user_cache[message.author.id]

            # Skip users not in db
            if user is None:
                continue

            # Insert new message event
            row = conv.new_message_to_row(user, message, client.event_type_map)
            client.db.add(db.MessageEvent, row)
            client.db.commit()

        log.info(f'Done')
        await msg.channel.send(res.get_string("messages.done"))

@cmdcoro
async def calc_message_stats(client: bot.Overlord, msg: discord.Message):
    new_message_stat_id = client.user_stat_type_id("new_message_count")
    delete_message_stat_id = client.user_stat_type_id("delete_message_count")

    new_message_event_id = client.event_type_id("new_message")
    delete_message_event_id = client.event_type_id("message_delete")

    # Tranaction begins
    async with client.sync():

        # Drop new message user stats
        log.warn(f'Dropping new message user stats')
        await msg.channel.send(res.get_string("messages.new_message_user_stat_drop"))
        client.db.query(db.UserStat).filter_by(type_id=new_message_stat_id).delete()
        client.db.commit()

        # Calc new message user stats
        log.warn(f'Calculating new message user stats')
        await msg.channel.send(res.get_string("messages.new_message_user_stat_calc"))
        select_query = q.select_message_count_per_user(new_message_event_id, [('type_id',new_message_stat_id)])
        insert_query = q.insert_user_stat_from_select(select_query)
        client.db.execute(insert_query)
        client.db.commit()

        # Drop delete message user stats
        log.warn(f'Dropping delete message user stats')
        await msg.channel.send(res.get_string("messages.delete_message_user_stat_drop"))
        client.db.query(db.UserStat).filter_by(type_id=delete_message_stat_id).delete()
        client.db.commit()

        # Calc delete message user stats
        log.warn(f'Calculating delete message user stats')
        await msg.channel.send(res.get_string("messages.delete_message_user_stat_calc"))
        select_query = q.select_message_count_per_user(delete_message_event_id, [('type_id',delete_message_stat_id)])
        insert_query = q.insert_user_stat_from_select(select_query)
        client.db.execute(insert_query)
        client.db.commit()

        log.info(f'Done')
        await msg.channel.send(res.get_string("messages.done"))

@cmdcoro
async def calc_vc_stats(client: bot.Overlord, msg: discord.Message):
    vc_time_stat_id = client.user_stat_type_id("vc_time")
    vc_join_event_id = client.event_type_id("vc_join")

    # Tranaction begins
    async with client.sync():

        # Drop vc time user stats
        log.warn(f'Dropping vc time user stats')
        await msg.channel.send(res.get_string("messages.vc_time_user_stat_drop"))
        client.db.query(db.UserStat).filter_by(type_id=vc_time_stat_id).delete()
        client.db.commit()

        # Calc vc time user stats
        log.warn(f'Calculating new message user stats')
        await msg.channel.send(res.get_string("messages.vc_time_user_stat_calc"))
        select_query = q.select_vc_time_per_user(vc_join_event_id, [('type_id',vc_time_stat_id)])
        insert_query = q.insert_user_stat_from_select(select_query)
        client.db.execute(insert_query)
        client.db.commit()

        log.info(f'Done')
        await msg.channel.send(res.get_string("messages.done"))

