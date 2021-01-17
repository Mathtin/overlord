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

def build_cmdcoro_usage(prefix: str, cmdname, func) -> str:
    f_args = func.__code__.co_varnames[:func.__code__.co_argcount]
    assert len(f_args) >= 2
    f_args = f_args[2:]
    args_str = ' ' + ' '.join(["{%s}" % arg for arg in f_args])
    return f'{prefix}{cmdname}' + args_str

def saving_original(o_dec: Callable[..., Any]) -> Callable[..., Any]:
    def wrapped(f: Callable[..., Awaitable[Any]]):
        if not hasattr(f, "original_func"):
            setattr(f, "original_func", f)
        or_func = f.original_func
        res_f = o_dec(f)
        setattr(res_f, "original_func", or_func)
        return res_f
    return wrapped

@saving_original
def cmdcoro(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    check_coroutine(func)
    or_func = func.original_func
    f_args = or_func.__code__.co_varnames[:or_func.__code__.co_argcount]
    assert len(f_args) >= 2
    f_args = f_args[2:]

    async def wrapped_func(client, message, prefix, argv):
        if len(f_args) != len(argv) - 1:
            usage_str = 'Usage: ' + build_cmdcoro_usage(prefix, argv[0], or_func)
            await message.channel.send(usage_str)
        else:
            await func(client, message, *argv[1:])
    
    return wrapped_func

@saving_original
def member_mention_arg(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    async def wrapped_func(ext, msg, user_mention, *argv):
        if len(msg.mentions) == 0:
            user = await ext.bot.resolve_user(user_mention)
            if user is None:
                await msg.channel.send(get_resource("messages.unknown_user"))
                return
            try:
                member = await ext.bot.guild.fetch_member(user.id)
            except discord.NotFound:
                await msg.channel.send(get_resource("messages.not_member_user"))
                return
        else:
            member = msg.mentions[0]
        if not is_user_member(member):
            await msg.channel.send(get_resource("messages.not_member_user"))
            return
        await func(ext, msg, member, *argv)
    return wrapped_func

@saving_original
def text_channel_mention_arg(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    async def wrapped_func(ext, msg, channel_mention, *argv):
        if len(msg.channel_mentions) == 0:
            await msg.channel.send(get_resource("messages.invalid_channel_mention"))
            return
        channel = msg.channel_mentions[0]
        if not is_text_channel(channel):
            await msg.channel.send(get_resource("messages.invalid_channel_type_text"))
            return
        await func(ext, msg, channel, *argv)
    return wrapped_func

###########################
# Bot model utility funcs #
###########################

def is_user_member(user: discord.User) -> bool:
    return isinstance(user, discord.Member)

def qualified_name(user: discord.User) -> str:
    return f'{user.name}#{user.discriminator}'

def quote_msg(msg: str) -> str:
    return '\n'.join(['> '+l for l in ('`'+msg.replace("`","\\`")+'`').splitlines()])

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
