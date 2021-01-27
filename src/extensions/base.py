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

import sys
import traceback
import asyncio
import logging
import discord

import util.resources as res

from discord.errors import InvalidArgument
from overlord.base import OverlordBase
from overlord.types import OverlordCommand, OverlordTask

from util import get_coroutine_attrs, limit_traceback, quote_msg
from util.exceptions import InvalidConfigException
from typing import Dict, List, Optional, Callable, Awaitable

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
    __enabled: bool
    __tasks: List[OverlordTask]
    __commands: Dict[str, OverlordCommand]
    __command_handlers: Dict[str, Callable[..., Awaitable[None]]]
    __task_instances: List[asyncio.AbstractEventLoop]
    __async_lock: asyncio.Lock

    def __init__(self, bot: OverlordBase, priority=None) -> None:
        super().__init__()
        self.bot = bot
        self.__enabled = False
        self.__async_lock = asyncio.Lock()

        attrs = [getattr(self, attr) for attr in dir(self) if not attr.startswith('_')]

        # Gather tasks
        self.__tasks =  [t for t in attrs if isinstance(t, OverlordTask)]
        self.__task_instances =  []

        # Gather commands
        self.__commands =  {c.name:c for c in attrs if isinstance(c, OverlordCommand)}
        self.__command_handlers =  {name:c.handler(self) for name, c in self.__commands.items()}

        # Reattach implemented handlers
        handlers = get_coroutine_attrs(self, name_filter=lambda x: x.startswith('on_'))
        for h_name, h in handlers.items():
            setattr(self, h_name, self.__handler(h))

        # Prioritize
        if priority is not None:
            self.__priority__ = priority
        if self.priority > 63 or self.priority < 0:
            raise InvalidArgument(f'priority should be less then 63 and bigger or equal then 0, got: {priority}')

    @staticmethod
    def task(*, seconds=0, minutes=0, hours=0, count=None, reconnect=True) -> Callable[..., Callable[..., Awaitable[None]]]:
        def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
            async def wrapped(self, *args, **kwargs):
                await self.bot.init_lock()
                await func(self, *args, **kwargs)
            return OverlordTask(wrapped, seconds=seconds, minutes=minutes, hours=hours, count=count, reconnect=reconnect)
        return decorator

    @staticmethod
    def command(name, desciption='') -> Callable[..., Callable[..., Awaitable[None]]]:
        def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
            return OverlordCommand(func, name=name, desciption=desciption)
        return decorator

    @staticmethod
    def __handler(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        async def wrapped(*args, **kwargs):
            if not func.__self__.__enabled:
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
        if self.__enabled:
            return
        self.__enabled = True
        self.__task_instances =  [t.task(self) for t in self.__tasks]
        for task in self.__task_instances:
            task.start()

    def stop(self) -> None:
        if not self.__enabled:
            return
        self.__enabled = False
        for task in self.__task_instances:
            task.stop()

    def sync(self) -> asyncio.Lock:
        return self.__async_lock

    def help_embed(self, name) -> discord.Embed:
        title = f'{self.__extname__}'
        help_page = self.bot.base_embed(name, title, self.__description__, self.__color__)
        commands = self.bot.config.command
        prefix = self.bot.prefix
        help_page
        for name, cmd in self.__commands.items():
            if name not in commands:
                help_page.add_field(name=f'[DISABLED] `{prefix}{name}`', value=cmd.help(prefix, []), inline=False)
            else:
                help_page.add_field(name=f'`$ {prefix}{name}`', value=cmd.help(prefix, commands[name]), inline=False)
        return help_page

    def cmd(self, name: str) -> Optional[OverlordCommand]:
        if name in self.__commands:
            return self.__commands[name]
        return None

    def cmd_handler(self, name: str) -> Optional[Callable[..., Awaitable[None]]]:
        if name in self.__command_handlers:
            return self.__command_handlers[name]
        return None

    @property
    def priority(self) -> int:
        return self.__priority__

    ####################
    # Default Handlers #
    ####################

    async def on_error(self, event, *args, **kwargs) -> None:
        """
            Async error event handler

            Sends stacktrace to error channel
        """
        ext_name = type(self).__name__
        ex = sys.exc_info()[1]

        logging.exception(f'Error from {ext_name} extension on event: {event}')

        exception_tb = traceback.format_exception(*sys.exc_info())
        exception_tb_limited = limit_traceback(exception_tb, "src", 4)
        exception_tb_quoted = quote_msg('\n'.join(exception_tb_limited))

        exception_msg = res.get("messages.dm_ext_exception").format(ext_name, event, str(ex)) + '\n' + exception_tb_quoted

        #exception_msg_short = f'`{str(ex)}` Reported to {self.bot.maintainer.mention}'

        #if self.bot.error_channel is not None:
        #    await self.bot.send_error(exception_msg_short)
        
        await self.bot.maintainer.send(exception_msg)
        self.stop()

    async def on_ready(self) -> None:
        pass
    