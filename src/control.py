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

#################
# Utility funcs #
#################

async def __drop_user_stats(client: bot.Overlord, stat_name: str, stat_id: int):
    log.warn(f'Dropping "{stat_name}" stats')
    answer = res.get("messages.user_stat_drop").format(stat_name)
    await client.control_channel.send(answer)
    client.db.query(db.UserStat).filter_by(type_id=stat_id).delete()
    client.db.commit()

async def __calc_user_stats(client: bot.Overlord, stat_name: str, stat_id: int, event_id: int, select_query):
    log.warn(f'Calculating "{stat_name}" stats')
    answer = res.get("messages.user_stat_calc").format(stat_name)
    await client.control_channel.send(answer)
    select_query = select_query(event_id, [('type_id',stat_id)])
    insert_query = q.insert_user_stat_from_select(select_query)
    client.db.execute(insert_query)
    client.db.commit()

def __build_stat_line(client: bot.Overlord, user: db.User, res_stat_name: str, stat_id_name: int):
    stat_name = res.get(f"messages.{res_stat_name}")
    stat_id = client.user_stat_type_id(stat_id_name)
    stat = q.get_user_stat_by_id(client.db, user.id, stat_id)
    stat_val = stat.value if stat is not None else 0
    return res.get("messages.user_stats_entry").format(stat_name, stat_val)

############################
# Control command Handlers #
############################


@cmdcoro
async def ping(client: bot.Overlord, msg: discord.Message):
    await msg.channel.send(res.get("messages.pong"))


@cmdcoro
async def sync_roles(client: bot.Overlord, msg: discord.Message):
    async with client.sync():
        await msg.channel.send(res.get("messages.sync_roles_begin"))
        await client.sync_roles()
        await msg.channel.send(res.get("messages.sync_users_begin"))
        await client.sync_users()
        await msg.channel.send(res.get("messages.done"))


@cmdcoro
async def reload_channel_history(client: bot.Overlord, msg: discord.Message, channel: str):
    # Resolve channel
    if len(msg.channel_mentions) == 0:
        await msg.channel.send(res.get("messages.invalid_channel_mention"))
        return
    channel = msg.channel_mentions[0]
    if not is_text_channel(channel):
        await msg.channel.send(res.get("messages.invalid_channel_type_text"))
        return

    # Tranaction begins
    async with client.sync():

        # Drop full channel message history
        log.warn(f'Dropping #{channel.name}({channel.id}) history')
        answer = res.get("messages.channel_history_drop").format(channel.mention)
        await msg.channel.send(answer)
        client.db.query(db.MessageEvent).filter_by(channel_id=channel.id).delete()
        client.db.commit()

        user_cache = {}

        # Load all messages
        log.warn(f'Loading #{channel.name}({channel.id}) history')
        answer = res.get("messages.channel_history_load").format(channel.mention)
        await msg.channel.send(answer)
        async for message in channel.history(limit=None,oldest_first=True):

            # Skip bot messages
            if message.author.bot:
                continue

            # Resolve user
            if message.author.id not in user_cache:
                user = q.get_user_by_did(client.db, message.author.id)
                if user is None and client.config["user.leave.keep"]:
                    user = client.db.add(db.User, conv.user_row(message.author))
                user_cache[message.author.id] = user
            else:
                user = user_cache[message.author.id]

            # Skip users not in db
            if user is None:
                continue

            # Insert new message event
            row = conv.new_message_to_row(user, message, client.event_type_map)
            client.db.add(db.MessageEvent, row)
            client.db.commit()

        log.info(f'Done')
        await msg.channel.send(res.get("messages.done"))


@cmdcoro
async def calc_message_stats(client: bot.Overlord, msg: discord.Message):
    # Tranaction begins
    async with client.sync():

        # Drop and recalculate "new message count" user stats
        stat_name = res.get("messages.new_message_user_stat")
        stat_id = client.user_stat_type_id("new_message_count")
        event_id = client.event_type_id("new_message")
        await __drop_user_stats(client, stat_name, stat_id)
        await __calc_user_stats(client, stat_name, stat_id, event_id, q.select_message_count_per_user)

        # Drop and recalculate "delete message count" user stats
        stat_name = res.get("messages.delete_message_user_stat")
        stat_id = client.user_stat_type_id("delete_message_count")
        event_id = client.event_type_id("message_delete")
        await __drop_user_stats(client, stat_name, stat_id)
        await __calc_user_stats(client, stat_name, stat_id, event_id, q.select_message_count_per_user)

        log.info(f'Done')
        await msg.channel.send(res.get("messages.done"))


@cmdcoro
async def calc_vc_stats(client: bot.Overlord, msg: discord.Message):
    # Tranaction begins
    async with client.sync():

        # Drop and recalculate "vc time" user stats
        stat_name = res.get("messages.vc_time_user_stat")
        stat_id = client.user_stat_type_id("vc_time")
        event_id = client.event_type_id("vc_join")
        await __drop_user_stats(client, stat_name, stat_id)
        await __calc_user_stats(client, stat_name, stat_id, event_id, q.select_vc_time_per_user)

        log.info(f'Done')
        await msg.channel.send(res.get("messages.done"))


@cmdcoro
async def get_user_stats(client: bot.Overlord, msg: discord.Message, username: str):
    # Resolve user
    if len(msg.mentions) == 0:
        await msg.channel.send(res.get("messages.invalid_user_mention"))
        return
    member = msg.mentions[0]
    user = q.get_user_by_did(client.db, member.id)
    if user is None:
        await msg.channel.send(res.get("messages.unknown_user"))
        return

    header = res.get("messages.user_stats_head").format(member.mention)
    new_msg_stat_line = __build_stat_line(client, user, "new_message_user_stat", "new_message_count")
    del_msg_stat_line = __build_stat_line(client, user, "delete_message_user_stat", "delete_message_count")
    vc_time_stat_line = __build_stat_line(client, user, "vc_time_user_stat", "vc_time")

    answer = f'{header}\n{new_msg_stat_line}\n{del_msg_stat_line}\n{vc_time_stat_line}\n'
    await msg.channel.send(answer)
    