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

from util import *
import util.resources as res

log = logging.getLogger('control')

#################
# Utility funcs #
#################

def __build_stat_line(client: bot.Overlord, user: db.User, stat: str, formatter=lambda x:str(x)):
    stat_name = res.get(f"messages.{stat}_stat")
    stat_val = client.s_stats.get(user, stat)
    stat_val_f = formatter(stat_val)
    return res.get("messages.user_stats_entry").format(stat_name, stat_val_f)

############################
# Control command Handlers #
############################

@cmdcoro
@text_channel_mention_arg
async def reload_channel_history(client: bot.Overlord, msg: discord.Message, channel: discord.TextChannel):
    permissions = channel.permissions_for(client.me)
    if not permissions.read_message_history:
        answer = res.get("messages.missing_access").format(channel.mention) + ' (can\'t read message history)'
        await msg.channel.send(answer)
        return

    # Tranaction begins
    async with client.sync():

        # Drop full channel message history
        log.warn(f'Dropping #{channel.name}({channel.id}) history')
        answer = res.get("messages.channel_history_drop").format(channel.mention)
        await msg.channel.send(answer)
        client.s_events.clear_text_channel_history(channel)

        # Load all messages
        log.warn(f'Loading #{channel.name}({channel.id}) history')
        answer = res.get("messages.channel_history_load").format(channel.mention)
        await msg.channel.send(answer)
        async for message in channel.history(limit=None,oldest_first=True):

            # Skip bot messages
            if message.author.bot:
                continue

            # Resolve user
            user = client.s_users.get(message.author)
            if user is None and client.config["user.leave.keep"]:
                user = client.s_users.add_user(message.author)

            # Skip users not in db
            if user is None:
                continue

            # Insert new message event
            client.s_events.create_new_message_event(user, message)

        log.info(f'Done')
        await msg.channel.send(res.get("messages.done"))


@cmdcoro
async def recalculate_stats(client: bot.Overlord, msg: discord.Message):
    # Tranaction begins
    async with client.sync():
        log.info(f"Recalculating all stats")
        answer = res.get("messages.user_stat_calc")
        await msg.channel.send(answer.format('all'))

        for stat_type in client.s_stats.user_stat_type_map:
            client.s_stats.reload_stat(stat_type)

        log.info(f'Done')
        await msg.channel.send(res.get("messages.done"))


@cmdcoro
@member_mention_arg
async def get_user_stats(client: bot.Overlord, msg: discord.Message, member: discord.Member):
    # Resolve user
    user = client.s_users.get(member)
    if user is None:
        await msg.channel.send(res.get("messages.unknown_user"))
        return

    answer = res.get("messages.user_stats_head").format(member.mention) + '\n'
    answer += __build_stat_line(client, user, "membership", formatter=pretty_days) + '\n'
    answer += __build_stat_line(client, user, "new_message_count") + '\n'
    answer += __build_stat_line(client, user, "delete_message_count") + '\n'
    answer += __build_stat_line(client, user, "edit_message_count") + '\n'
    answer += __build_stat_line(client, user, "vc_time", formatter=pretty_seconds) + '\n'

    if client.s_stats.get(user, "min_weight") > 0:
        answer += __build_stat_line(client, user, "min_weight") + '\n'
    if client.s_stats.get(user, "max_weight") > 0:
        answer += __build_stat_line(client, user, "max_weight") + '\n'
    if client.s_stats.get(user, "exact_weight") > 0:
        answer += __build_stat_line(client, user, "exact_weight") + '\n'

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
        client.set_awaiting_sync()
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
    client.update_config(new_config.bot)
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
        if parent_config['logger']:
            logging.config.dictConfig(parent_config['logger'])
        client.update_config(parent_config.bot)
    except (InvalidConfigException, TypeError) as e:
        log.warn(f'Invalid config value provided: {value}, reason: {e}. Reverting.')
        parent_config.alter(path, old_value)
        if parent_config['logger']:
            logging.config.dictConfig(parent_config['logger'])
        client.update_config(parent_config.bot)
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
async def add_rank(client: bot.Overlord, msg: discord.Message, role_name: str, weight: str, membership: str, msg_count: str, vc_time: str):
    try:
        weight = int(weight)
        membership = int(membership)
        messages_count = int(msg_count)
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
        "membership": membership,
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
async def edit_rank(client: bot.Overlord, msg: discord.Message, role_name: str, weight: str, membership: str, msg_count: str, vc_time: str):
    try:
        weight = int(weight)
        membership = int(membership)
        messages_count = int(msg_count)
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
        "membership": membership,
        "messages": messages_count,
        "vc": vc_time
    }
    path = 'bot.ranks.role'

    if await __safe_alter_config(client, path, ranks):
        __save_config(client)
        log.info(f'Done')
        await client.control_channel.send(res.get("messages.done"))


@cmdcoro
async def get_stat_names(client: bot.Overlord, msg: discord.Message):
    names = [res.get("messages.stats_name_entry").format(s) for s in client.s_stats.user_stat_type_map]
    answer = res.get("messages.stats_name_head") + '\n' + '\n'.join(names)
    await msg.channel.send(answer)

@cmdcoro
@member_mention_arg
async def get_user_stat(client: bot.Overlord, msg: discord.Message, member: discord.Member, stat_name: str):
    user = client.s_users.get(member)
    if user is None:
        await msg.channel.send(res.get("messages.unknown_user"))
        return

    try:
        answer = __build_stat_line(client, user, stat_name)
        await msg.channel.send(answer)
    except NameError:
        await msg.channel.send(res.get("messages.error").format("Invalid stat name"))
        return

@cmdcoro
@member_mention_arg
async def set_user_stat(client: bot.Overlord, msg: discord.Message, member: discord.Member, stat_name: str, value: str):
    try:
        value = int(value)
    except ValueError:
        await msg.channel.send(res.get("messages.error").format("integer expected"))
        return
    
    if value < 0:
        await msg.channel.send(res.get("messages.warning").format("negative stat value!"))

    user = client.s_users.get(member)
    if user is None:
        await msg.channel.send(res.get("messages.unknown_user"))
        return

    try:
        client.s_stats.set(user, stat_name, value)
        await client.control_channel.send(res.get("messages.done"))
    except NameError:
        await msg.channel.send(res.get("messages.error").format("Invalid stat name"))
        return
