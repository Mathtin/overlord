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
import sys
import traceback
import asyncio
import logging

import discord
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
# Main class implementation #
#############################

class Overlord(discord.Client):
    __async_lock: asyncio.Lock
    __initialized: bool
    __awaiting_role_sync: bool
    __awaiting_user_sync: bool
    __awaiting_user_sync: bool

    # Members loaded from ENV
    token: str
    guild_id: int
    control_channel_id: int
    error_channel_id: int

    # Members passed via constructor
    config: ConfigView
    db: DB.DBSession

    # Values initiated on_ready
    guild: discord.Guild
    control_channel: discord.TextChannel
    error_channel: discord.TextChannel
    me: discord.Member

    # Services
    s_users: UserService
    s_roles: RoleService
    s_events: EventService
    s_stats: StatService
    s_ranking: RankingService

    # Scheduled tasks
    tasks: List[asyncio.AbstractEventLoop]

    def __init__(self, config: ConfigView, db_session: DB.DBSession):
        self.__async_lock = asyncio.Lock()
        self.__initialized = False
        self.__awaiting_role_sync = True
        self.__awaiting_user_sync = True
        self.tasks = []

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

        # Map event types
        self.event_type_map = {row.name:row.id for row in self.db.query(DB.EventType)}
        self.user_stat_type_map = {row.name:row.id for row in self.db.query(DB.UserStatType)}

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
        roles = self.config["control.roles"]
        return len(filter_roles(user, roles)) > 0

    ################
    # Sync methods #
    ################

    def run(self):
        super().run(self.token)

    def check_config(self):
        admin_roles = self.config["control.roles"]
        for role_name in admin_roles:
            if self.get_role(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", "bot.control.roles")
        # Check ranks config
        self.s_ranking.check_config()

    def update_config(self, config: ConfigView):
        self.config = config
        self.s_ranking.config = config.ranks
        self.check_config()

    #################
    # Async methods #
    #################

    async def init_lock(self):
        while not self.__initialized:
            await asyncio.sleep(0.1)
        return

    async def send_error(self, msg: str):
        if self.error_channel is not None:
            await self.error_channel.send(res.get("messages.error").format(msg))
        return

    async def set_awaiting_sync(self):
        if self.__awaiting_role_sync and self.__awaiting_user_sync:
            return
        self.__awaiting_role_sync = True
        self.__awaiting_user_sync = True
        await self.send_warning('Awaiting role syncronization')

    async def send_warning(self, msg: str):
        if self.error_channel is not None:
            await self.error_channel.send(res.get("messages.warning").format(msg))
        return

    async def sync_roles(self):
        log.info('Syncing roles')
        # Update role service
        self.s_roles.load(self.guild.roles)
        # Drop awaiting flag
        self.__awaiting_role_sync = False
        log.info('Syncing roles done')

    async def sync_users(self):
        # Check awaiting flag
        if self.__awaiting_role_sync:
            log.error(f'Cannot sync users: awaiting role sync')
            await self.send_error(f'Cannot sync users: awaiting role sync')
            return
        log.info(f'Syncing users')
        # Mark everyone absent
        self.s_users.mark_everyone_absent()
        # Reload
        async for member in self.guild.fetch_members(limit=None):
            # Cache and skip bots
            if member.bot:
                self.s_users.cache_bot(member)
                continue
            # Update and repair
            user = self.s_users.update_member(member)
            self.s_events.repair_member_joined_event(member, user)
        # Remove effectively absent
        if not self.config["user.leave.keep"]:
            self.s_users.remove_absent()
        self.__awaiting_user_sync = False
        log.info(f'Syncing users done')

    async def update_user_rank(self, member: discord.Member):
        if self.__awaiting_role_sync:
            log.error("Cannot update user rank: awaiting role sync")
            await self.send_error(f'Cannot update user rank: awaiting role sync')
            return
        # Resolve user
        user = self.s_users.get(member)
        # Skip non-existing users
        if user is None:
            log.warn(f'{qualified_name(member)} does not exist in db! Skipping user rank update!')
            return
        # Ignore special roles
        if self.s_ranking.ignore_member(member):
            return
        # Resolve roles to move
        roles_add, roles_del = self.s_ranking.roles_to_add_and_remove(member, user)
        # Remove old roles
        if roles_del:
            log.info(f"Removing {qualified_name(member)}'s rank roles: {roles_del}")
            await member.remove_roles(*roles_del)
        # Add new roles
        if roles_add:
            log.info(f"Adding {qualified_name(member)}'s rank roles: {roles_add}")
            await member.add_roles(*roles_add)
        # Update user in db
        self.s_users.update_member(member)

    async def update_user_ranks(self):
        if self.__awaiting_role_sync:
            log.error("Cannot update user ranks: awaiting role sync")
            await self.send_error(f'Cannot update user ranks: awaiting role sync')
            return
        log.info(f'Updating user ranks')
        async for member in self.guild.fetch_members(limit=None):
            # Cache and skip bots
            if member.bot:
                self.s_users.cache_bot(member)
                continue
            await self.update_user_rank(member)
        log.info(f'Done updating user ranks')

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

    async def logout(self):
        for task in self.tasks:
            task.cancel()
        await super().logout()

    #########
    # Hooks #
    #########

    async def on_error(self, event, *args, **kwargs):
        """
            Async error event handler

            Sends stacktrace to error channel
        """
        ex_type = sys.exc_info()[0]
        ex = sys.exc_info()[1]

        logging.exception(f'Error on event: {event}')

        # exception_lines = traceback.format_exception(*sys.exc_info())
        # exception_msg = '`' + ''.join(exception_lines).replace('`', '\'')[:1800] + '`'
        exception_msg_short = f'`{str(ex)}`\nBlame <@281130377488236554>'

        if self.error_channel is not None:
            await self.send_error(exception_msg_short)

        if ex_type is InvalidConfigException:
            await self.logout()
        if ex_type is NotCoroutineException:
            await self.logout()


    async def on_ready(self):
        """
            Async ready event handler

            Completly initialize bot state
        """
        # Lock current async context
        async with self.sync():
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

            # Sync roles and users
            await self.sync_roles()
            await self.sync_users()

            # Check config value
            self.check_config()

            # Schedule tasks
            self.tasks.append(self.s_stats.get_stat_update_task(self.sync(), hours=24, loop=asyncio.get_running_loop()))
            for task in self.tasks:
                task.start()
            
            # Message for pterodactyl panel
            print(self.config["egg_done"])
            self.__initialized = True


    @after_initialized
    @event_config("message.new")
    @skip_bots
    @guild_member_event
    async def on_message(self, message: discord.Message):
        """
            Async new message event handler

            Saves event in database
        """
        # handle control commands seperately
        if message.channel == self.control_channel:
            await self.on_control_message(message)
            return
        # Sync code part
        async with self.sync():
            user = self.s_users.get(message.author)
            # Skip non-existing users
            if user is None:
                log.warn(f'{qualified_name(message.author)} does not exist in db! Skipping new message event!')
                return
            # Save event
            self.s_events.create_new_message_event(user, message)
            # Update stats
            inc_value = self.s_stats.get(user, 'new_message_count') + 1
            self.s_stats.set(user, 'new_message_count', inc_value)
            # Update user rank
            await self.update_user_rank(message.author)


    async def on_control_message(self, message: discord.Message):
        """
            Async new control message event handler

            Calls appropriate control callback
        """
        if not self.is_admin(message.author):
            return

        prefix = self.config["control.prefix"]
        argv = parse_control_message(prefix, message)

        if argv is None or len(argv) == 0:
            return
            
        cmd_name = argv[0]

        control_hooks = self.config["commands"]

        if cmd_name == "help":
            help_lines = []
            line_fmt = res.get("messages.commands_list_entry")
            for cmd in control_hooks:
                hook = get_module_element(control_hooks[cmd])
                base_line = build_cmdcoro_usage(prefix, cmd, hook.or_cmdcoro)
                help_lines.append(line_fmt.format(base_line))
            help_header = res.get("messages.commands_list_head")
            help_msg = '\n'.join(help_lines)
            await message.channel.send(f'{help_header}\n{help_msg}\n')
            return

        if cmd_name not in control_hooks:
            await message.channel.send(res.get("messages.unknown_command"))
            return

        if self.__awaiting_role_sync or self.__awaiting_user_sync:
            await self.send_warning('Awaiting role syncronization')
        
        hook = get_module_element(control_hooks[cmd_name])
        check_coroutine(hook)
        await hook(self, message, prefix, argv)

    
    @after_initialized
    @event_config("message.edit")
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
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
            # Update stats
            inc_value = self.s_stats.get(msg.user, 'edit_message_count') + 1
            self.s_stats.set(msg.user, 'edit_message_count', inc_value)
            # Update user rank
            member = await self.guild.fetch_member(msg.user.did)
            await self.update_user_rank(member)

    
    @after_initialized
    @event_config("message.delete")
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
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
            # Update stats
            inc_value = self.s_stats.get(msg.user, 'delete_message_count') + 1
            self.s_stats.set(msg.user, 'delete_message_count', inc_value)
            # Update user rank
            member = await self.guild.fetch_member(msg.user.did)
            await self.update_user_rank(member)

    
    @after_initialized
    @event_config("user.join")
    @skip_bots
    @guild_member_event
    async def on_member_join(self, member: discord.Member):
        """
            Async member join event handler

            Saves user in database
        """
        if self.__awaiting_user_sync:
            return
        # Sync code part
        async with self.sync():
            # Add/update user
            user = self.s_users.update_member(member)
            # Add event
            self.s_events.create_member_join_event(user, member)

    
    @after_initialized
    @event_config("user.update")
    @skip_bots
    @guild_member_event
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
            Async member remove event handler

            Removes user from database (or keep it, depends on config)
        """
        if self.__awaiting_user_sync:
            return
        # track only role/nickname change
        if not (before.roles != after.roles or \
                before.display_name != after.display_name or \
                before.name != after.name or \
                before.discriminator != after.discriminator):
            return
        # Skip absent
        if self.s_users.get(before) is None:
            log.warn(f'{qualified_name(after)} does not exist in db! Skipping user update event!')
            return
        # Sync code part
        async with self.sync():
            # Update user
            self.s_users.update_member(after)

    
    @after_initialized
    @event_config("user.leave")
    @skip_bots
    @guild_member_event
    async def on_member_remove(self, member: discord.Member):
        """
            Async member remove event handler

            Removes user from database (or keep it, depends on config)
        """
        # Sync code part
        async with self.sync():
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

    
    @after_initialized
    @skip_bots
    @guild_member_event
    async def on_voice_state_update(self, user: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """
            Async vc state change event handler

            Saves event in database
        """
        if before.channel == after.channel:
            return
        if before.channel is not None and self.check_afk_state(before):
            await self.on_vc_leave(user, before.channel)
        if after.channel is not None and self.check_afk_state(after):
            await self.on_vc_join(user, after.channel)
            
    
    @event_config("voice.join")
    async def on_vc_join(self, member: discord.Member, channel: discord.VoiceChannel):
        """
            Async vc join event handler

            Saves event in database
        """
        # Sync code part
        async with self.sync():
            user = self.s_users.get(member)
            # Skip non-existing users
            if user is None:
                log.warn(f'{qualified_name(member)} does not exist in db! Skipping vc join event!')
                return
            # Apply constraints
            self.s_events.repair_vc_leave_event(user, channel)
            # Save event
            self.s_events.create_vc_join_event(user, channel)
            
    
    @event_config("voice.leave")
    async def on_vc_leave(self, member: discord.Member, channel: discord.VoiceChannel):
        """
            Async vc join event handler

            Saves event in database
        """
        # Sync code part
        async with self.sync():
            user = self.s_users.get(member)
            # Skip non-existing users
            if user is None:
                log.warn(f'{qualified_name(member)} does not exist in db! Skipping vc leave event!')
                return
            # Close event
            join_event = self.s_events.close_vc_join_event(user, channel)
            if join_event is None:
                return
            # Update stats
            stat_val = self.s_stats.get(user, 'vc_time')
            stat_val += (join_event.updated_at - join_event.created_at).total_seconds()
            self.s_stats.set(user, 'vc_time', stat_val)
            # Update user rank
            await self.update_user_rank(member)

    async def on_guild_role_create(self, role: discord.Role):
        if self.__awaiting_role_sync and self.__awaiting_user_sync:
            return
        self.__awaiting_role_sync = True
        self.__awaiting_user_sync = True
        await self.send_warning('New role detected. Awaiting role syncronization.')

    async def on_guild_role_delete(self, role: discord.Role):
        if self.__awaiting_role_sync and self.__awaiting_user_sync:
            return
        self.__awaiting_role_sync = True
        self.__awaiting_user_sync = True
        await self.send_warning('Role remove detected. Awaiting role syncronization.')

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if self.__awaiting_role_sync and self.__awaiting_user_sync:
            return
        self.__awaiting_role_sync = True
        self.__awaiting_user_sync = True
        await self.send_warning('Role change detected. Awaiting role syncronization.')


