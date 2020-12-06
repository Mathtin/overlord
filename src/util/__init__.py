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

from os import replace
from .config import ConfigView
from .exceptions import InvalidConfigException, NotCoroutineException
from .resources import get as get_resource

import importlib
import os.path
import asyncio
import shlex
import discord

#################
# Utility Funcs #
#################

__module_cache = {}
def get_module_element(path: str):
    splited_path = path.split('.')
    module_name = '.'.join(splited_path[:-1])
    object_name = splited_path[-1]
    if module_name not in __module_cache:
        __module_cache[module_name] = importlib.import_module(module_name)
    module = __module_cache[module_name]
    return getattr(module, object_name)

def dict_fancy_table(values: dict, key_name='name'):
    if not values:
        return '++\n'*2

    col0 = [key_name] + list(values.keys())
    row_count = len(col0)
    col_names = list(values[col0[-1]].keys())

    to_col = lambda k: [k] + [values[v][k] for v in values]
    table = [col0] + [to_col(k) for k in col_names]

    col_width = lambda col: max(len(str(v)) for v in col)
    cols_width = [col_width(col) for col in table]

    cols_format = [f'{{:{w}}}' for w in cols_width]
    str_row_values = lambda i: [cols_format[j].format(col[i]) for (j,col) in enumerate(table)]
    format_line = lambda i: '| ' + ' | '.join(str_row_values(i)) + ' |\n'
    separator = '+-' + '-+-'.join(['-'*w for w in cols_width]) + '-+\n'

    lines = [format_line(i) for i in range(row_count)]
    return separator + separator.join(lines) + separator


def parse_control_message(prefix: str, message: discord.Message):
    prefix_len = len(prefix)
    msg = message.content.strip()

    msg_prefix = msg[: prefix_len]
    msg_suffix = msg[prefix_len :]

    if msg_prefix != prefix or msg_suffix == "":
        return None

    lines = [l.strip() for l in msg_suffix.splitlines()]
    res = shlex.split(lines[0])
    lines = lines[1:]
    merging = False
    merging_val = ''
    for line in lines:
        if line[:2] == '> ':
            if merging:
                merging_val += '\n' + line[2:]
            else:
                merging = True
                merging_val = line[2:]
            continue
        elif merging:
            res.append(merging_val)
            merging = False
            merging_val = ''
        res += shlex.split(line)
    if merging:
        res.append(merging_val)

    return res

def check_coroutine(func):
    if not asyncio.iscoroutinefunction(func):
        raise NotCoroutineException(func)

def build_cmdcoro_usage(prefix: str, cmdname, func):
    f_args = func.__code__.co_varnames[:func.__code__.co_argcount]
    assert len(f_args) >= 2
    f_args = f_args[2:]
    args_str = ' ' + ' '.join(["{%s}" % arg for arg in f_args])
    return f'{prefix}{cmdname}' + args_str

def cmdcoro(func):
    check_coroutine(func)

    f_args = func.__code__.co_varnames[:func.__code__.co_argcount]
    assert len(f_args) >= 2
    f_args = f_args[2:]

    async def wrapped_func(client, message, prefix, argv):
        if len(f_args) != len(argv) - 1:
            usage_str = 'Usage: ' + build_cmdcoro_usage(prefix, argv[0], func)
            await message.channel.send(usage_str)
        else:
            await func(client, message, *argv[1:])

    if hasattr(func, "or_cmdcoro"):
        setattr(wrapped_func, "or_cmdcoro", func.or_cmdcoro)
    else:
        setattr(wrapped_func, "or_cmdcoro", func)
    
    return wrapped_func

def member_mention_arg(func):
    async def wrapped_func(client, msg, user_mention, *argv):
        if len(msg.mentions) == 0:
            await msg.channel.send(get_resource("messages.invalid_user_mention"))
            return
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
