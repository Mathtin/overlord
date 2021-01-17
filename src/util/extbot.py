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
from typing import Any, Callable, Dict, List, Awaitable, Optional, Union
import discord
import asyncio

from discord.channel import TextChannel
from .resources import get as get_resource
from .exceptions import InvalidConfigException, NotCoroutineException

#############################
# Bot control coro wrappers #
#############################

def check_coroutine(func) -> None:
    if not asyncio.iscoroutinefunction(func):
        raise NotCoroutineException(func)

def get_coroutine_attrs(obj: Any, filter=lambda x:True, name_filter=lambda x:True) -> Dict[str, Callable[..., Awaitable[Any]]]:
    attrs = {attr:getattr(obj, attr) for attr in dir(obj) if name_filter(attr)}
    return {name:f for name,f in attrs.items() if asyncio.iscoroutinefunction(f) and filter(f)}

def get_loop_attrs(obj: Any, filter=lambda x:True, name_filter=lambda x:True) -> List[asyncio.AbstractEventLoop]:
    attrs = [getattr(obj, attr) for attr in dir(obj) if name_filter(attr)]
    return [l for l in attrs if isinstance(l, asyncio.AbstractEventLoop) and filter(l)]

###########################
# Bot model utility funcs #
###########################

def is_user_member(user: discord.User) -> bool:
    return isinstance(user, discord.Member)

def qualified_name(user: discord.User) -> str:
    return f'{user.name}#{user.discriminator}'

def quote_msg(msg: str) -> str:
    return '\n'.join([f'> `{l}`' for l in msg.replace("`","\\`").splitlines()])

def get_channel_env_var_name(n) -> str:
    return f'DISCORD_CHANNEL_{n}'

def get_channel_id(n) -> Optional[int]:
    var_name = get_channel_env_var_name(n)
    try:
        res = os.environ.get(var_name)
        return int(res) if res is not None else None
    except ValueError as e:
        raise InvalidConfigException(str(e), var_name)

def is_text_channel(channel) -> bool:
    return channel.type == discord.ChannelType.text

def is_dm_message(message: discord.Message) -> bool:
    return isinstance(message.channel, discord.DMChannel)

def is_same_author(m1: discord.Message, m2: discord.Message) -> bool:
    return m1.author.id == m2.author.id

def is_role_applied(user: discord.Member, role: Union[discord.Role, str]) -> bool:
    if isinstance(role, discord.Role):
        return is_role_applied(user, role.name)
    for r in user.roles:
        if r.name == role:
            return True
    return False

def filter_roles(user: discord.Member, roles_filter: List[Union[discord.Role, str]]) -> List[Union[discord.Role, str]]:
    res = []
    for r in roles_filter:
        if is_role_applied(user, r):
            res.append(r)
    return res

async def send_long_line(channel: discord.TextChannel, line: str):
    chunk = 2000
    parts = [ line[i:i+chunk] for i in range(0, len(len), chunk) ]
    for part in parts:
        await channel.send(channel, part)

async def send_long_message(channel: discord.TextChannel, message: str):
    lines = message.splitlines()
    cur = ''
    for line in lines:
        if not cur:
            if len(line) > 2000:
                await send_long_line(channel, message)
            else:
                cur = line
        else: # if smth in cur
            if len(line) > 2000:
                await send_long_line(channel, message)
            elif len(cur) + len(line) < 2000:
                cur += '\n' + line
            else: # if len(cur) + len(line) > 2000
                await channel.send(cur)
                cur = line
    if cur:
        await channel.send(cur)
        
            

    