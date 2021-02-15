#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################
# ........../\./\...___......|\.|..../...\.........#
# ........./..|..\/\.|.|_|._.|.\|....|.c.|.........#
# ......../....../--\|.|.|.|i|..|....\.../.........#
#        Mathtin (c)                              #
###################################################
#   Project: Overlord discord bot                 #
#   Author: Daniel [Mathtin] Shiko                #
#   Copyright (c) 2020 <wdaniil@mail.ru>          #
#   This file is released under the MIT license.  #
###################################################

__author__ = 'Mathtin'

import asyncio
import logging
import sys
import traceback
from typing import Dict, List, Optional, Callable, Awaitable

import discord
from discord.errors import InvalidArgument

from overlord.base import OverlordBase
from overlord.command import OverlordCommand
from overlord.types import OverlordTask
from util import get_coroutine_attrs
from util.exceptions import InvalidConfigException
from util.resources import R

log = logging.getLogger('overlord-extension')


############################
# Bot Extension Base Class #
############################

class BotExtension(object):

    __priority__ = 0
    __extname__ = 'Base Extension'
    __description__ = 'Base bot extension class'
    __color__ = 0x7B838A

    # Members passed via constructor
    bot: OverlordBase

    # State members
    _enabled: bool
    _tasks: List[OverlordTask]
    _commands: Dict[str, OverlordCommand]
    _command_handlers: Dict[str, Callable[..., Awaitable[None]]]
    _task_instances: List[asyncio.AbstractEventLoop]
    _async_lock: asyncio.Lock

    def __init__(self, bot: OverlordBase, priority=None) -> None:
        super().__init__()
        self.bot = bot
        self._enabled = False
        self._async_lock = asyncio.Lock()

        attrs = [getattr(self, attr) for attr in dir(self) if not attr.startswith('_')]

        # Gather tasks
        self._tasks = [t for t in attrs if isinstance(t, OverlordTask)]
        self._task_instances = []

        # Gather commands
        self._commands = {c.name: c for c in attrs if isinstance(c, OverlordCommand)}
        self._command_handlers = {name: c.handler(self) for name, c in self._commands.items()}

        # Reattach implemented handlers
        handlers = get_coroutine_attrs(self, name_filter=lambda x: x.startswith('on_'))
        for h_name, h in handlers.items():
            setattr(self, h_name, self._handler(h))

        # Prioritize
        if priority is not None:
            self.__priority__ = priority
        if self.priority > 63 or self.priority < 0:
            raise InvalidArgument(f'priority should be less then 63 and bigger or equal then 0, got: {priority}')

    @staticmethod
    def task(*, seconds=0, minutes=0, hours=0, count=None, reconnect=True) -> \
            Callable[[Callable[..., Awaitable[None]]], OverlordTask]:

        def decorator(func: Callable[..., Awaitable[None]]) -> OverlordTask:

            async def wrapped(self, *args, **kwargs) -> None:
                await self.bot.init_lock()
                await func(self, *args, **kwargs)

            return OverlordTask(wrapped, seconds=seconds, minutes=minutes, hours=hours, count=count,
                                reconnect=reconnect)
        return decorator

    @staticmethod
    def command(name, description='') -> Callable[[Callable[..., Awaitable[None]]], OverlordCommand]:

        def decorator(func: Callable[..., Awaitable[None]]) -> OverlordCommand:
            return OverlordCommand(func, name=name, description=description)

        return decorator

    @staticmethod
    def _handler(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        async def wrapped(*args, **kwargs):
            if not func.__self__._enabled:
                return
            await func.__self__.bot.init_lock()
            try:
                await func(*args, **kwargs)
            except InvalidConfigException as e:
                raise e
            except:
                await func.__self__.on_error(func.__name__, *args, **kwargs)

        return wrapped

    @property
    def name(self):
        return self.__extname__

    def start(self) -> None:
        if self._enabled:
            return
        self._enabled = True
        self._task_instances = [t.task(self) for t in self._tasks]
        for task in self._task_instances:
            task.start()

    def stop(self) -> None:
        if not self._enabled:
            return
        self._enabled = False
        for task in self._task_instances:
            task.stop()

    def sync(self) -> asyncio.Lock:
        return self._async_lock

    def help_embed(self, name) -> discord.Embed:
        title = f'{self.__extname__}'
        help_page = self.bot.new_embed(title, self.__description__, header=name, color=self.__color__)
        commands = self.bot.config.command
        prefix = self.bot.prefix
        for name, cmd in self._commands.items():
            if name not in commands or not commands[name]:
                help_page.add_field(name=f'[DISABLED] {prefix}{name}', value=cmd.help(prefix, []), inline=False)
            else:
                help_page.add_field(name=f'`$ {prefix}{commands[name][0]}`', value=cmd.help(prefix, commands[name]),
                                    inline=False)
        return help_page

    def cmd(self, name: str) -> Optional[OverlordCommand]:
        if name in self._commands:
            return self._commands[name]
        return None

    def cmd_handler(self, name: str) -> Optional[Callable[..., Awaitable[None]]]:
        if name in self._command_handlers:
            return self._command_handlers[name]
        return None

    @property
    def priority(self) -> int:
        return self.__priority__

    ####################
    # Default Handlers #
    ####################

    async def on_error(self, event, *_, **__) -> None:
        """
            Async error event handler

            Sends stacktrace to error channel
        """
        ext_name = type(self).__name__
        logging.exception(f'Error from {ext_name} extension on event: {event}')

        ex_type = sys.exc_info()[0]
        ex = sys.exc_info()[1]
        tb = traceback.format_exception(*sys.exc_info())
        name = ex_type.__name__

        reported_to = f'{R.MESSAGE.STATUS.REPORTED_TO} {self.bot.maintainer.mention}'
        details = f'{str(ex)}\n**{R.NAME.COMMON.EXTENSION} {ext_name}**, disabled'

        maintainer_report = self.bot.new_error_report(name, details, tb)
        channel_report = self.bot.new_error_report(name, str(ex) + '\n' + reported_to)

        if self.bot.log_channel is not None and event != 'on_ready':
            await self.bot.log_channel.send(embed=channel_report)

        await self.bot.maintainer.send(embed=maintainer_report)

        self.stop()

    async def on_ready(self) -> None:
        pass
