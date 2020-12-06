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

import json
import logging

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
    stat_val = client.get_user_stat(user, stat_id_name)
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
async def update_user_ranks(client: bot.Overlord, msg: discord.Message):
    async with client.sync():
        await msg.channel.send(res.get("messages.update_ranks_begin"))
        await client.update_user_ranks()
        await msg.channel.send(res.get("messages.done"))


@cmdcoro
@member_mention_arg
async def update_user_rank(client: bot.Overlord, msg: discord.Message, member: discord.Member):
    async with client.sync():
        user = q.get_user_by_did(client.db, member.id)
        if user is None:
            await msg.channel.send(res.get("messages.unknown_user"))
            return
        await msg.channel.send(res.get("messages.update_rank_begin").format(member.mention))
        await client.update_user_rank(user, member)
        await msg.channel.send(res.get("messages.done"))


@cmdcoro
@text_channel_mention_arg
async def reload_channel_history(client: bot.Overlord, msg: discord.Message, channel: discord.TextChannel):
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
@member_mention_arg
async def get_user_stats(client: bot.Overlord, msg: discord.Message, member: discord.Member):
    # Resolve user
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
    
@cmdcoro
async def clear_data(client: bot.Overlord, msg: discord.Message):

    models = [db.MemberEvent, db.MessageEvent, db.VoiceChatEvent, db.UserStat, db.User, db.Role]
    table_data_drop = res.get("messages.table_data_drop")

    # Tranaction begins
    async with client.sync():
        log.warn("Clearing database")
        await client.send_warning("Clearing database")
        for model in models:
            log.warn(f"Clearing table `{model.table_name()}`")
            await client.control_channel.send(table_data_drop.format(model.table_name()))
            client.db.query(model).delete()
            client.db.commit()
        await client.set_awaiting_sync()
        log.info(f'Done')
        await client.control_channel.send(res.get("messages.done"))

@cmdcoro
async def reload_config(client: bot.Overlord, msg: discord.Message):
    log.info(f'Reloading config')
    # Reload config
    parent_config = client.config.parent()
    new_config = ConfigView(path=parent_config.fpath(), schema_name="config_schema")
    if new_config['logger']:
        logging.config.dictConfig(new_config['logger'])
    client.config = new_config.bot
    log.info(f'Done')
    await client.control_channel.send(res.get("messages.done"))

def __save_config(client: bot.Overlord):
    log.warn(f'Dumping raw config')
    parent_config = client.config.parent()
    with open(parent_config.fpath(), "w") as f:
        json.dump(parent_config.value(), f, indent=4)

@cmdcoro
async def save_config(client: bot.Overlord, msg: discord.Message):
    log.info(f'Saving config')
    __save_config(client)
    log.info(f'Done')
    await client.control_channel.send(res.get("messages.done"))

@cmdcoro
async def get_config_value(client: bot.Overlord, msg: discord.Message, path: str):
    parent_config = client.config.parent()
    try:
        value = parent_config[path]
        value_s = quote_msg(json.dumps(value, indent=4))
        header = res.get("messages.config_value_header")
        await client.control_channel.send(f'{header}\n{value_s}')
    except KeyError:
        await client.control_channel.send(res.get("messages.invalid_config_path"))

async def __safe_alter_config(client: bot.Overlord, path: str, value):
    parent_config = client.config.parent()

    try:
        old_value = parent_config[path]
    except KeyError:
        log.info(f'Invalid config path provided: {path}')
        await client.control_channel.send(res.get("messages.invalid_config_path"))
        return False

    try:
        log.warn(f'Altering raw config path {path}')
        parent_config.alter(path, value)
        client.check_config()
    except (InvalidConfigException, TypeError) as e:
        log.warn(f'Invalid config value provided: {value}, reason: {e}. Reverting.')
        parent_config.alter(path, old_value)
        msg = res.get("messages.error").format(e) + '\n' + res.get("messages.warning").format('Config reverted')
        await client.control_channel.send(msg)
        return False
    
    return True

@cmdcoro
async def alter_config(client: bot.Overlord, msg: discord.Message, path: str, value: str):
    try:
        value_obj = json.loads(value)
    except json.decoder.JSONDecodeError:
        log.info(f'Invalid json value provided: {value}')
        await client.control_channel.send(res.get("messages.invalid_json_value"))
        return

    if await __safe_alter_config(client, path, value_obj):
        log.info(f'Done')
        await client.control_channel.send(res.get("messages.done"))

@cmdcoro
async def get_ranks(client: bot.Overlord, msg: discord.Message):
    ranks = client.config["ranks.role"]
    table_header = res.get('messages.rank_table_header')
    table = dict_fancy_table(ranks, key_name='rank')
    await msg.channel.send(f'{table_header}\n{quote_msg(table)}')

@cmdcoro
async def add_rank(client: bot.Overlord, msg: discord.Message, role_name: str, weight: str, messages_count: str, vc_time: str):
    try:
        weight = int(weight)
        messages_count = int(messages_count)
        vc_time = int(vc_time)
    except ValueError:
        await msg.channel.send(res.get("messages.rank_arg_parse_error"))
        return
    role = client.get_role(role_name)
    if role is None:
        await msg.channel.send(res.get("messages.rank_role_unknown").format(role_name))
        return
    ranks = client.config.ranks.role.copy().value()
    if role_name in ranks:
        await msg.channel.send(res.get("messages.rank_role_exists"))
        return
    ranks_weights = {ranks[r]['weight']:r for r in ranks}
    if weight in ranks_weights:
        await msg.channel.send(res.get("messages.rank_role_same_weight").format(ranks_weights[weight]))
        return
    ranks[role_name] = {
        "weight": weight,
        "messages": messages_count,
        "vc": vc_time
    }
    path = 'bot.ranks.role'

    if await __safe_alter_config(client, path, ranks):
        __save_config(client)
        log.info(f'Done')
        await client.control_channel.send(res.get("messages.done"))

@cmdcoro
async def remove_rank(client: bot.Overlord, msg: discord.Message, role_name: str):
    role = client.get_role(role_name)
    if role is None:
        await msg.channel.send(res.get("messages.rank_role_unknown").format(role_name))
        return
    ranks = client.config.ranks.role.copy().value()
    if role_name not in ranks:
        await msg.channel.send(res.get("messages.rank_unknown"))
        return
    del ranks[role_name]
    path = 'bot.ranks.role'

    if await __safe_alter_config(client, path, ranks):
        __save_config(client)
        log.info(f'Done')
        await client.control_channel.send(res.get("messages.done"))

@cmdcoro
async def edit_rank(client: bot.Overlord, msg: discord.Message, role_name: str, weight: str, messages_count: str, vc_time: str):
    try:
        weight = int(weight)
        messages_count = int(messages_count)
        vc_time = int(vc_time)
    except ValueError:
        await msg.channel.send(res.get("messages.rank_arg_parse_error"))
        return
    role = client.get_role(role_name)
    if role is None:
        await msg.channel.send(res.get("messages.rank_role_unknown").format(role_name))
        return
    ranks = client.config.ranks.role.copy().value()
    if role_name not in ranks:
        await msg.channel.send(res.get("messages.rank_unknown"))
        return
    ranks_weights = {ranks[r]['weight']:r for r in ranks}
    if weight in ranks_weights and ranks_weights[weight] != role_name:
        await msg.channel.send(res.get("messages.rank_role_same_weight").format(ranks_weights[weight]))
        return
    ranks[role_name] = {
        "weight": weight,
        "messages": messages_count,
        "vc": vc_time
    }
    path = 'bot.ranks.role'

    if await __safe_alter_config(client, path, ranks):
        __save_config(client)
        log.info(f'Done')
        await client.control_channel.send(res.get("messages.done"))
