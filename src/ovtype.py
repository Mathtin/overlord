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

from typing import Any
import db as DB
import discord as DIS
import asyncio
from util import check_coroutine
from discord.ext import tasks

###################
# Generic Objects #
###################

class OverlordGenericObject(object):

    db: Any
    discord: Any

    def __init__(self, discord, db) -> None:
        super().__init__()
        self.discord = discord
        self.db = db

class OverlordRole(OverlordGenericObject):
    db: DB.Role
    discord: DIS.Role

class OverlordUser(OverlordGenericObject):
    db: DB.User
    discord: DIS.User

class OverlordMember(OverlordUser):
    discord: DIS.Member

class OverlordMessage(OverlordGenericObject):
    db: DB.MessageEvent
    discord: DIS.Message

class OverlordMessageEdit(OverlordMessage):
    discord: DIS.RawMessageUpdateEvent

class OverlordMessageDelete(OverlordMessage):
    discord: DIS.RawMessageDeleteEvent

class OverlordVCState(OverlordGenericObject):
    db: DB.VoiceChatEvent
    discord: DIS.VoiceState

#################################
# Bot Extension Utility Classes #
#################################

class OverlordTask(object):

    def __init__(self, func, seconds=0, minutes=0, hours=0, count=None, reconnect=True) -> None:
        super().__init__()
        self.func = func
        self.kwargs = {
            'seconds': seconds,
            'minutes': minutes,
            'hours': hours,
            'count': count,
            'reconnect': reconnect
        }

    def task(self, ext) -> asyncio.AbstractEventLoop:
        self.kwargs['loop'] = asyncio.get_running_loop()
        async def method(*args, **kwargs):
            try:
                await self.func(ext, *args, **kwargs)
            except:
                await ext.on_error(self.func.__name__, *args, **kwargs)
        return tasks.loop(**self.kwargs)(method)
    
class OverlordCommand(object):

    def __init__(self, func, name, desciption='') -> None:
        super().__init__()
        check_coroutine(func)
        self.func = func
        self.name = name
        self.desciption = desciption
        f_args = func.__code__.co_varnames[:func.__code__.co_argcount]
        assert len(f_args) >= 2
        self.f_args = f_args[2:]
        self.args_str = ' '.join(["{%s}" % arg for arg in self.f_args])

    def usage(self, prefix: str, cmdname: str) -> str:
        return f'{prefix}{cmdname} {self.args_str}'

    def handler(self, ext):
        async def wrapped_func(message, prefix, argv):
            if len(self.f_args) != len(argv) - 1:
                usage_str = 'Usage: ' + self.usage(prefix, argv[0])
                await message.channel.send(usage_str)
            else:
                try:
                    await self.func(ext, message, *argv[1:])
                except:
                    await ext.on_error(self.func.__name__, message, *argv[1:])
        return wrapped_func
