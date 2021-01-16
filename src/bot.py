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

from datetime import datetime
import os
import sys
import traceback
import asyncio
import logging

import discord
from discord.errors import InvalidArgument
from ovtype import *
import db as DB

from util import *
import util.resources as res
from typing import Dict, List, Optional
from services import EventService, RankingService, RoleService, StatService, UserService

log = logging.getLogger('overlord-bot')

######################
# Utility decorators #
######################

def after_initialized(func):
    async def _func(self, *args, **kwargs):
        await self.init_lock()
        return await func(self, *args, **kwargs)
    return _func

def skip_bots(func):
    async def _func(self, obj, *args, **kwargs):
        if isinstance(obj, discord.User) or isinstance(obj, discord.Member):
            if obj.bot:
                return
        elif isinstance(obj, discord.Message): 
            if obj.author.bot:
                return
        return await func(self, obj, *args, **kwargs)
    return _func

def guild_member_event(func):
    async def _func(self, obj, *args, **kwargs):
        if isinstance(obj, discord.Member):
            if not self.is_guild_member(obj):
                return
        elif isinstance(obj, discord.Message): 
            if not self.is_guild_member_message(obj):
                return
        return await func(self, obj, *args, **kwargs)
    return _func

def event_config(name: str):
    def wrapper(func):
        async def _func(self, *args, **kwargs):
            if not self.config[f"event.{name}.track"]:
                return
            return await func(self, *args, **kwargs)
        return _func
    return wrapper

#############################
# Base class implementation #
#############################

class OverlordBase(discord.Client):
    __async_lock: asyncio.Lock
    __initialized: bool
    __awaiting_sync: bool
    __awaiting_sync_last_updated: datetime

    # Members loaded from ENV
    token: str
    guild_id: int
    control_channel_id: int
    error_channel_id: int
    maintainer_id: int

    # Members passed via constructor
    config: ConfigView
    db: DB.DBSession

    # Values initiated on_ready
    guild: discord.Guild
    control_channel: discord.TextChannel
    error_channel: discord.TextChannel
    maintainer: discord.User
    me: discord.Member

    # Services
    s_users: UserService
    s_roles: RoleService
    s_events: EventService
    s_stats: StatService
    s_ranking: RankingService

    def __init__(self, config: ConfigView, db_session: DB.DBSession) -> None:
        self.__async_lock = asyncio.Lock()
        self.__initialized = False
        self.__awaiting_sync = True
        self.__awaiting_sync_last_updated = datetime.now()

        self.config = config
        self.db = db_session

        # Init base class
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.voice_states = True

        super().__init__(intents=intents)

        # Load env values
        self.token = os.getenv('DISCORD_TOKEN')
        self.guild_id = int(os.getenv('DISCORD_GUILD'))
        self.control_channel_id = int(os.getenv('DISCORD_CONTROL_CHANNEL'))
        self.error_channel_id = int(os.getenv('DISCORD_ERROR_CHANNEL'))
        self.maintainer_id = int(os.getenv('MAINTAINER_DISCORD_ID'))

        # Preset values initiated on_ready
        self.guild = None
        self.control_channel = None
        self.error_channel = None
        self.me = None

        # Services
        self.s_roles = RoleService(self.db)
        self.s_users = UserService(self.db, self.s_roles)
        self.s_events = EventService(self.db)
        self.s_stats = StatService(self.db, self.s_events)
        self.s_ranking = RankingService(self.s_stats, self.s_roles, self.config.ranks)

    ###########
    # Getters #
    ###########

    def sync(self) -> asyncio.Lock:
        return self.__async_lock

    def is_guild_member(self, member: discord.Member) -> bool:
        return member.guild.id == self.guild.id

    def is_guild_member_message(self, msg: discord.Message) -> bool:
        return not is_dm_message(msg) and msg.guild.id == self.guild.id

    def check_afk_state(self, state: discord.VoiceState) -> bool:
        return not state.afk or not self.config["event.voice.afk.ignore"]

    def is_special_channel_id(self, channel_id: int) -> bool:
        return channel_id == self.control_channel.id or channel_id == self.error_channel.id

    def get_role(self, role_name: str) -> Optional[discord.Role]:
        return self.s_roles.get(role_name)

    def is_admin(self, user: discord.Member) -> bool:
        if user == self.maintainer:
            return True
        roles = self.config["control.roles"]
        return len(filter_roles(user, roles)) > 0

    def awaiting_sync(self) -> bool:
        return self.__awaiting_sync

    def awaiting_sync_elapsed(self) -> int:
        if not self.__awaiting_sync:
            return 0
        return (datetime.now() - self.__awaiting_sync_last_updated).total_seconds()

    ################
    # Sync methods #
    ################

    def run(self) -> None:
        super().run(self.token)

    def check_config(self) -> None:
        admin_roles = self.config["control.roles"]
        for role_name in admin_roles:
            if self.get_role(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", "bot.control.roles")
        # Check ranks config
        self.s_ranking.check_config()

    def update_config(self, config: ConfigView) -> None:
        self.config = config
        self.s_ranking.config = config.ranks
        self.check_config()

    def set_awaiting_sync(self) -> None:
        self.__awaiting_sync_last_updated = datetime.now()
        self.__awaiting_sync = True

    def unset_awaiting_sync(self) -> None:
        self.__awaiting_sync_last_updated = datetime.now()
        self.__awaiting_sync = False

    #################
    # Async methods #
    #################

    async def init_lock(self) -> None:
        while not self.__initialized:
            await asyncio.sleep(0.1)
        return

    async def send_error(self, msg: str) -> None:
        if self.error_channel is not None:
            await self.error_channel.send(res.get("messages.error").format(msg))
        await self.maintainer.send(res.get("messages.error").format(msg))
        return

    async def send_warning(self, msg: str) -> None:
        if self.error_channel is not None:
            await self.error_channel.send(res.get("messages.warning").format(msg))
        return

    async def sync_users(self) -> None:
        log.info('Syncing roles')
        self.s_roles.load(self.guild.roles)

        log.info(f'Syncing users')
        # Mark everyone absent
        self.s_users.mark_everyone_absent()
        # Reload
        async for member in self.guild.fetch_members(limit=None):
            # Cache and skip bots
            if member.bot:
                continue
            # Update and repair
            user = self.s_users.update_member(member)
            self.s_events.repair_member_joined_event(member, user)
        # Remove effectively absent
        if not self.config["user.leave.keep"]:
            self.s_users.remove_absent()
        self.unset_awaiting_sync()
        log.info(f'Syncing users done')

    async def resolve_user(self, user_mention: str) -> Optional[discord.User]:
            try:
                if '#' in user_mention:
                    user = self.s_users.get_by_qualified_name(user_mention)
                else:
                    user = self.s_users.get_by_display_name(user_mention)
                if user is None:
                    return None
                return await self.fetch_user(user.did)
            except discord.NotFound:
                return None
            except ValueError:
                return None

    async def logout(self) -> None:
        await super().logout()

    #########
    # Hooks #
    #########

    async def on_error(self, event, *args, **kwargs) -> None:
        """
            Async error event handler

            Sends stacktrace to error channel
        """
        ex_type = sys.exc_info()[0]
        ex = sys.exc_info()[1]

        logging.exception(f'Error on event: {event}')

        exception_tb = traceback.format_exception(*sys.exc_info())
        exception_tb_limited = limit_traceback(exception_tb, "bot.py", 6)
        exception_tb_quoted = quote_msg('\n'.join(exception_tb_limited))

        exception_msg = res.get("messages.dm_bot_exception").format(str(ex)) + '\n' + exception_tb_quoted

        exception_msg_short = f'`{str(ex)}` Reported to {self.maintainer.mention}'

        if self.error_channel is not None:
            await self.send_error(exception_msg_short)
        
        await self.maintainer.send(exception_msg)

        if ex_type is InvalidConfigException:
            await self.logout()
        if ex_type is NotCoroutineException:
            await self.logout()
        if event == 'on_ready':
            await self.logout()

    async def on_ready(self) -> None:
        """
            Async ready event handler

            Completly initialize bot state
        """
        # Find guild
        self.guild = self.get_guild(self.guild_id)
        if self.guild is None:
            raise InvalidConfigException("Discord server id is invalid", "DISCORD_GUILD")
        log.info(f'{self.user} is connected to the following guild: {self.guild.name}(id: {self.guild.id})')

        self.me = await self.guild.fetch_member(self.user.id)

        # Attach control channel
        channel = self.get_channel(self.control_channel_id)
        if channel is None:
            raise InvalidConfigException(f'Control channel id is invalid', 'DISCORD_CONTROL_CHANNEL')
        if not is_text_channel(channel):
            raise InvalidConfigException(f"{channel.name}({channel.id}) is not text channel",'DISCORD_CONTROL_CHANNEL')
        log.info(f'Attached to {channel.name} as control channel ({channel.id})')
        self.control_channel = channel

        # Attach error channel
        if self.error_channel_id:
            channel = self.get_channel(self.error_channel_id)
            if channel is None:
                raise InvalidConfigException(f'Error channel id is invalid', 'DISCORD_ERROR_CHANNEL')
            if not is_text_channel(channel):
                raise InvalidConfigException(f"{channel.name}({channel.id}) is not text channel",'DISCORD_ERROR_CHANNEL')
            log.info(f'Attached to {channel.name} as error channel ({channel.id})')
            self.error_channel = channel

        # Resolve maintainer
        try:
            self.maintainer = await self.fetch_user(self.maintainer_id)
            await self.maintainer.send('Starting instance')
        except discord.NotFound:
            raise InvalidConfigException(f'Error maintainer id is invalid', 'MAINTAINER_DISCORD_ID')
        except discord.Forbidden:
            raise InvalidConfigException(f'Error cannot send messagees to maintainer', 'MAINTAINER_DISCORD_ID')
        log.info(f'Maintainer is {qualified_name(self.maintainer)} ({self.maintainer.id})')

        # Sync roles and users
        await self.sync_users()

        # Check config value
        self.check_config()

        self.__initialized = True

############################
# Bot Extension Base Class #
############################

class BotExtension(object):

    __priority__ = 0

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
            except:
                await func.__self__.on_error(func.__name__, *args, **kwargs)
        return wrapped

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
        exception_tb_limited = limit_traceback(exception_tb, "bot.py", 4)
        exception_tb_quoted = quote_msg('\n'.join(exception_tb_limited))

        exception_msg = res.get("messages.dm_ext_exception").format(ext_name, str(ex)) + '\n' + exception_tb_quoted

        #exception_msg_short = f'`{str(ex)}` Reported to {self.bot.maintainer.mention}'

        #if self.bot.error_channel is not None:
        #    await self.bot.send_error(exception_msg_short)
        
        await self.bot.maintainer.send(exception_msg)
        self.stop()

    async def on_ready(self) -> None:
        pass
    

#############################
# Main class implementation #
#############################

class Overlord(OverlordBase):
    
    # Extensions
    __extensions: List[BotExtension]
    __handlers: Dict[str, Callable[..., Awaitable[None]]]
    __call_plan_map: Dict[str, List[Callable[..., Awaitable[None]]]]
    __cmd_cache: Dict[str, Callable[..., Awaitable[None]]]

    def __init__(self, config: ConfigView, db_session: DB.DBSession) -> None:
        super().__init__(config, db_session)
        self.__extensions = []
        self.__handlers = get_coroutine_attrs(self, name_filter=lambda x: x.startswith('on_'))

    def extend(self, extension: BotExtension) -> None:
        self.__extensions.append(extension)
        self.__extensions.sort(key=lambda e: e.priority)
        self.__call_plan_map = {}
        for h in self.__handlers:
            self.__build_call_plan(h)

    def __build_call_plan(self, handler_name) -> None:
        if handler_name == 'on_error':
            return
        # Build call plan
        call_plan = [[] for i in range(64)]
        for extension in self.__extensions:
            if not hasattr(extension, handler_name):
                continue
            call_plan[extension.priority].append(getattr(extension, handler_name))
        self.__call_plan_map[handler_name] = [call for call in call_plan if call]

    async def __run_call_plan(self, name: str, *args, **kwargs):
        call_plan = self.__call_plan_map[name]
        for handlers in call_plan:
            calls = [h(*args, **kwargs) for h in handlers]
            await asyncio.wait(calls)

    def logout(self) -> None:
        for ext in self.__extensions:
            ext.stop()
        return super().logout()

    def __find_cmd_handler(self, name: str) -> Callable[..., Awaitable[None]]:
        for ext in self.__extensions:
            handler = ext.cmd_handler(name)
            if handler is not None:
                return handler
        raise InvalidConfigException(f"Command handler not found for {name}", "bot.commands")

    def update_command_cache(self) -> None:
        commands = self.config["commands"]
        self.__cmd_cache = {}
        for cmd, aliases in commands.items():
            handler = self.__find_cmd_handler(cmd)
            self.__cmd_cache[cmd] = handler
            for alias in aliases:
                if alias in self.__cmd_cache:
                    raise InvalidConfigException(f"Command alias collision for {alias}: {cmd} <-> {self.__cmd_cache[alias]}", "bot.commands")
                self.__cmd_cache[alias] = handler
        
    def update_config(self, config: ConfigView) -> None:
        super().update_config(config)
        self.update_command_cache()

    #########
    # Hooks #
    #########

    async def on_ready(self) -> None:
        async with self.sync():
            await super().on_ready()
            self.update_command_cache()
            # Start extensions
            for ext in self.__extensions:
                ext.start()
            # Call 'on_ready' extension handlers
            await self.__run_call_plan('on_ready')
            # Message for pterodactyl panel
            print(self.config["egg_done"])
            await self.maintainer.send('Started!')


    @after_initialized
    @event_config("message.new")
    @skip_bots
    async def on_message(self, message: discord.Message) -> None:
        """
            Async new message event handler

            Saves event in database
        """
        # handle control commands seperately
        if message.channel == self.control_channel or (message.author == self.maintainer and is_dm_message(message)):
            await self._on_control_message(message)
            return
        if not self.is_guild_member_message(message):
            return
        user = self.s_users.get(message.author)
        # Skip non-existing users
        if user is None:
            log.warn(f'{qualified_name(message.author)} does not exist in db! Skipping new message event!')
            return
        # Save event
        msg = self.s_events.create_new_message_event(user, message)
        # Call extension 'on_message' handlers
        await self.__run_call_plan('on_message', OverlordMessage(message, msg))


    async def _on_control_message(self, message: discord.Message) -> None:
        """
            Async new control message event handler

            Calls appropriate control callback
        """
        # Filter non-admins
        if not self.is_admin(message.author):
            return
        # Parse argv
        prefix = self.config["control.prefix"]
        argv = parse_control_message(prefix, message)
        if argv is None or len(argv) == 0:
            return
        # Resolve cmd handler
        cmd_name = argv[0]
        if cmd_name not in self.__cmd_cache:
            await message.channel.send(res.get("messages.unknown_command"))
            return
        handler = self.__cmd_cache[cmd_name]
        # Call handler
        await handler(message, prefix, argv)

    
    @after_initialized
    @event_config("message.edit")
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        """
            Async message edit event handler

            Saves event in database
        """
        if self.is_special_channel_id(payload.channel_id):
            return
        # ingore absent
        msg = self.s_events.get_message(payload.message_id)
        if msg is None:
            return
        # Sync code part
        async with self.sync():
            self.s_events.create_message_edit_event(msg)
        # Call extension 'on_message_edit' handlers
        await self.__run_call_plan('on_message_edit', OverlordMessageEdit(payload, msg))

    
    @after_initialized
    @event_config("message.delete")
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """
            Async message delete event handler

            Saves event in database
        """
        if self.is_special_channel_id(payload.channel_id):
            return
        # ingore absent
        msg = self.s_events.get_message(payload.message_id)
        if msg is None:
            return
        # Sync code part
        async with self.sync():
            self.s_events.create_message_delete_event(msg)
        # Call extension 'on_message_delete' handlers
        await self.__run_call_plan('on_message_delete', OverlordMessageDelete(payload, msg))
    

    @after_initialized
    @event_config("user.join")
    @skip_bots
    @guild_member_event
    async def on_member_join(self, member: discord.Member) -> None:
        """
            Async member join event handler

            Saves user in database
        """
        if self.awaiting_sync():
            return
        # Add/update user
        user = self.s_users.update_member(member)
        # Add event
        self.s_events.create_member_join_event(user, member)
        # Call extension 'on_member_join' handlers
        await self.__run_call_plan('on_member_join', OverlordMember(member, user))

    
    @after_initialized
    @event_config("user.update")
    @skip_bots
    @guild_member_event
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """
            Async member remove event handler

            Removes user from database (or keep it, depends on config)
        """
        if self.awaiting_sync():
            return
        # track only role/nickname change
        if not (before.roles != after.roles or \
                before.display_name != after.display_name or \
                before.name != after.name or \
                before.discriminator != after.discriminator):
            return
        # Skip absent
        user = self.s_users.get(before)
        if user is None:
            log.warn(f'{qualified_name(after)} does not exist in db! Skipping user update event!')
            return
        # Update user
        self.s_users.update_member(after)
        # Call extension 'on_member_update' handlers
        await self.__run_call_plan('on_member_update', OverlordMember(before, user), OverlordMember(after, user))

    
    @after_initialized
    @event_config("user.leave")
    @skip_bots
    @guild_member_event
    async def on_member_remove(self, member: discord.Member) -> None:
        """
            Async member remove event handler

            Removes user from database (or keep it, depends on config)
        """
        if self.config["user.leave.keep"]:
            user = self.s_users.mark_absent(member)
            if user is None:
                log.warn(f'{qualified_name(member)} does not exist in db! Skipping user leave event!')
                return
            self.s_events.create_user_leave_event(user)
        else:
            user = self.s_users.remove(member)
            if user is None:
                log.warn(f'{qualified_name(member)} does not exist in db! Skipping user leave event!')
                return
        # Call extension 'on_member_remove' handlers
        await self.__run_call_plan('on_member_remove', OverlordMember(member, user))

    
    @after_initialized
    @skip_bots
    @guild_member_event
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """
            Async vc state change event handler

            Saves event in database
        """
        if before.channel == after.channel:
            return
        if before.channel is not None and self.check_afk_state(before):
            await self.on_vc_leave(member, before)
        if after.channel is not None and self.check_afk_state(after):
            await self.on_vc_join(member, after)
            
    
    @event_config("voice.join")
    async def on_vc_join(self, member: discord.Member, state: discord.VoiceState) -> None:
        """
            Async vc join event handler

            Saves event in database
        """
        user = self.s_users.get(member)
        # Skip non-existing users
        if user is None:
            log.warn(f'{qualified_name(member)} does not exist in db! Skipping vc join event!')
            return
        # Apply constraints
        self.s_events.repair_vc_leave_event(user, state.channel)
        # Save event
        event = self.s_events.create_vc_join_event(user, state.channel)
        # Call extension 'on_vc_join' handlers
        await self.__run_call_plan('on_vc_join', OverlordUser(member, user), OverlordVCState(state, event))
            
    
    @event_config("voice.leave")
    async def on_vc_leave(self, member: discord.Member, state: discord.VoiceState) -> None:
        """
            Async vc join event handler

            Saves event in database
        """
        user = self.s_users.get(member)
        # Skip non-existing users
        if user is None:
            log.warn(f'{qualified_name(member)} does not exist in db! Skipping vc leave event!')
            return
        # Close event
        events = self.s_events.close_vc_join_event(user, state.channel)
        if events is None:
            return
        join_event, leave_event = events
        # Call extension 'on_vc_leave' handlers
        await self.__run_call_plan('on_vc_leave', OverlordUser(member, user), OverlordVCState(state, join_event), OverlordVCState(state, leave_event))

    async def on_guild_role_create(self, role: discord.Role) -> None:
        if role.guild != self.guild:
            return
        if self.awaiting_sync():
            return
        self.set_awaiting_sync()
        await self.send_warning('New role detected. Awaiting role syncronization.')
        # Call extension 'on_guild_role_create' handlers
        await self.__run_call_plan('on_guild_role_create', OverlordRole(role, self.s_roles.get(role.name)))

    async def on_guild_role_delete(self, role: discord.Role) -> None:
        if role.guild != self.guild:
            return
        if self.awaiting_sync():
            return
        self.set_awaiting_sync()
        await self.send_warning('Role remove detected. Awaiting role syncronization.')
        # Call extension 'on_guild_role_delete' handlers
        await self.__run_call_plan('on_guild_role_delete', OverlordRole(role, self.s_roles.get(role.name)))

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        if before.guild != self.guild:
            return
        if self.awaiting_sync():
            return
        self.set_awaiting_sync()
        await self.send_warning('Role change detected. Awaiting role syncronization.')
        role = self.s_roles.get(before.name)
        # Call extension 'on_guild_role_update' handlers
        await self.__run_call_plan('on_guild_role_update', OverlordRole(before, role), OverlordRole(after, role))

##################
# Sync Extension #
##################

class UserSyncExtension(BotExtension):

    @BotExtension.task(seconds=1)
    async def user_sync_task(self):
        if self.bot.awaiting_sync_elapsed() < 30:
            return
        log.info("Scheduled user sync update")
        async with self.bot.sync():
            await self.bot.sync_users()
        log.info("Done scheduled user sync update")
            
    ############
    # Commands #
    ############

    @BotExtension.command("ping", desciption="Checks bot state")
    async def cmd_ping(self, msg: discord.Message):
        if self.bot.sync().locked():
            await msg.channel.send(res.get("messages.busy"))
        else:
            await msg.channel.send(res.get("messages.pong"))

    @BotExtension.command("sync", desciption="Syncronize db data with guild data in terms of users and roles")
    async def cmd_sync_roles(self, msg: discord.Message):
        async with self.bot.sync():
            await msg.channel.send(res.get("messages.sync_users_begin"))
            await self.bot.sync_users()
            await msg.channel.send(res.get("messages.done"))

