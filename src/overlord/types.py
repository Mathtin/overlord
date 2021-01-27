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

from typing import Any, Dict, List
import db as DB
import discord as DIS
import asyncio
from util import check_coroutine, ConfigView
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

class OverlordReaction(OverlordGenericObject):
    db: DB.ReactionEvent
    discord: DIS.PartialEmoji

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
        self.req_f_args = [a for a in self.f_args if not a.lower().startswith('optional')]
        self.args_str = ' '.join(["{%s}" % arg for arg in self.f_args])

    def usage(self, prefix: str, cmdname: str) -> str:
        return f'{prefix}{cmdname} {self.args_str}'

    def help(self, prefix: str, aliases: List[str]) -> str:
        aliases_str = ' ,'.join([f'`{prefix}{a}`' for a in aliases])
        return f'Usage: `{prefix}{self.name} {self.args_str}`\n' + \
            f'{self.desciption}\n' + \
            f'Aliases: {aliases_str}\n'

    def handler(self, ext):
        async def wrapped_func(message, prefix, argv):
            cmd = argv[0]
            argv = argv[1:]
            if len(self.req_f_args) > len(argv) or len(argv) > len(self.f_args):
                usage_str = 'Usage: ' + self.usage(prefix, cmd)
                await message.channel.send(usage_str)
            else:
                try:
                    await self.func(ext, message, *argv)
                except:
                    await ext.on_error(self.func.__name__, message, prefix, argv)
        return wrapped_func

class OverlordControlConfig(ConfigView):
    """
    control {
        prefix = "..."
        roles = [...]
        channel = ...
    }
    """
    prefix  : str       = "ov/"
    roles   : List[str] = ["Overlord"]
    channel : int       = 0

class OverlordRootConfig(ConfigView):
    """
    bot {
        control : OverlordControlConfig
        keep_absent_users = ...
        ignore_afk_vc = ...
        command {
            help = ["help", ...]
            ...
        }
    }
    """
    control           : OverlordControlConfig = OverlordControlConfig()
    keep_absent_users : bool                  = True
    ignore_afk_vc     : bool                  = True
    egg_done          : str                   = "change this part"
    command           : Dict[str, List[str]]  = {}
    
