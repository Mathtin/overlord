#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2020-present Daniel [Mathtin] Shiko <wdaniil@mail.ru>
Project: Overlord discord bot
Contributors: Danila [DeadBlasoul] Popov <dead.blasoul@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__author__ = "Mathtin"

import asyncio
from typing import Any, Dict, List

import discord as DIS
from discord.ext import tasks

import db as DB
from util import ConfigView


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
            except KeyboardInterrupt:
                raise
            except:
                await ext.on_error(self.func.__name__, *args, **kwargs)

        return tasks.loop(**self.kwargs)(method)


class OverlordControlConfig(ConfigView):
    """
    control {
        prefix = "..."
        roles = [...]
        channel = ...
    }
    """
    prefix: str = "ov/"
    roles: List[str] = ["Overlord"]
    channel: int = 0


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
    control: OverlordControlConfig = OverlordControlConfig()
    keep_absent_users: bool = True
    ignore_afk_vc: bool = True
    egg_done: str = "change this part"
    command: Dict[str, List[str]] = {}
