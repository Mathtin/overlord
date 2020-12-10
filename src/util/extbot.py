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

import os
import discord
from .resources import get as get_resource
from .exceptions import InvalidConfigException

#############################
# Bot control coro wrappers #
#############################

def member_mention_arg(func):
    async def wrapped_func(client, msg, user_mention, *argv):
        if len(msg.mentions) == 0:
            user = await client.resolve_user(user_mention)
            if user is None:
                await msg.channel.send(get_resource("messages.unknown_user"))
                return
            try:
                member = await client.guild.fetch_member(user.id)
            except discord.NotFound:
                await msg.channel.send(get_resource("messages.not_member_user"))
                return
        else:
            member = msg.mentions[0]
        if not is_user_member(member):
            await msg.channel.send(get_resource("messages.not_member_user"))
            return
        await func(client, msg, member, *argv)

    if hasattr(func, "or_cmdcoro"):
        setattr(wrapped_func, "or_cmdcoro", func.or_cmdcoro)
    else:
        setattr(wrapped_func, "or_cmdcoro", func)
    
    return wrapped_func

def text_channel_mention_arg(func):
    async def wrapped_func(client, msg, channel_mention, *argv):
        if len(msg.channel_mentions) == 0:
            await msg.channel.send(get_resource("messages.invalid_channel_mention"))
            return
        channel = msg.channel_mentions[0]
        if not is_text_channel(channel):
            await msg.channel.send(get_resource("messages.invalid_channel_type_text"))
            return
        await func(client, msg, channel, *argv)

    if hasattr(func, "or_cmdcoro"):
        setattr(wrapped_func, "or_cmdcoro", func.or_cmdcoro)
    else:
        setattr(wrapped_func, "or_cmdcoro", func)
    
    return wrapped_func

###########################
# Bot model utility funcs #
###########################

def is_user_member(user: discord.User):
    return isinstance(user, discord.Member)

def qualified_name(user: discord.User):
    return f'{user.name}#{user.discriminator}'

def quote_msg(msg: str):
    return '\n'.join(['> '+l for l in ('`'+msg.replace("`","\\`")+'`').splitlines()])

def get_channel_env_var_name(n):
    return f'DISCORD_CHANNEL_{n}'

def get_channel_id(n):
    var_name = get_channel_env_var_name(n)
    try:
        res = os.environ.get(var_name)
        return int(res) if res is not None else None
    except ValueError as e:
        raise InvalidConfigException(str(e), var_name)

def is_text_channel(channel):
    return channel.type == discord.ChannelType.text

def is_dm_message(message: discord.Message):
    return isinstance(message.channel, discord.DMChannel)

def is_same_author(m1: discord.Message, m2: discord.Message):
    return m1.author.id == m2.author.id

def is_role_applied(user: discord.Member, role):
    if isinstance(role, discord.Role):
        return is_role_applied(user, role.name)
    for r in user.roles:
        if r.name == role:
            return True
    return False

def filter_roles(user: discord.Member, roles_filter: list):
    res = []
    for r in roles_filter:
        if is_role_applied(user, r):
            res.append(r)
    return res
