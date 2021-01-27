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
import json
import os
import sys
import traceback
import asyncio
import logging

import discord
import db as DB

from util import limit_traceback
from util.config import ConfigManager
from util.exceptions import InvalidConfigException, NotCoroutineException
from util.extbot import is_dm_message, filter_roles, quote_msg, is_text_channel, qualified_name
import util.resources as res
from typing import Any, List, Optional, Union
from services import EventService, RoleService, StatService, UserService

from .types import OverlordRootConfig

log = logging.getLogger('overlord-bot')

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
    cnf_manager: ConfigManager
    config: OverlordRootConfig
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

    def __init__(self, cnf_manager: ConfigManager, db_session: DB.DBSession) -> None:
        self.__async_lock = asyncio.Lock()
        self.__initialized = False
        self.__awaiting_sync = True
        self.__awaiting_sync_last_updated = datetime.now()

        self.cnf_manager = cnf_manager
        self.config = cnf_manager.find_section(OverlordRootConfig)
        self.db = db_session

        # Init base class
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.voice_states = True
        intents.reactions = True

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

    ###########
    # Getters #
    ###########

    @property
    def extensions(self) -> List[Any]:
        pass

    @property
    def prefix(self) -> str:
        return self.config.control.prefix

    def sync(self) -> asyncio.Lock:
        return self.__async_lock

    def is_guild_member(self, member: discord.Member) -> bool:
        return member.guild.id == self.guild.id

    def is_guild_member_message(self, msg: discord.Message) -> bool:
        return not is_dm_message(msg) and msg.guild.id == self.guild.id

    def check_afk_state(self, state: discord.VoiceState) -> bool:
        return not state.afk or not self.config.ignore_afk_vc

    def is_special_channel_id(self, channel_id: int) -> bool:
        return channel_id == self.control_channel.id or channel_id == self.error_channel.id

    def get_role(self, role_name: str) -> Optional[discord.Role]:
        return self.s_roles.get(role_name)

    def is_admin(self, user: discord.Member) -> bool:
        if user == self.maintainer:
            return True
        return len(filter_roles(user, self.config.control.roles)) > 0

    def awaiting_sync(self) -> bool:
        return self.__awaiting_sync

    def awaiting_sync_elapsed(self) -> int:
        if not self.__awaiting_sync:
            return 0
        return (datetime.now() - self.__awaiting_sync_last_updated).total_seconds()

    def base_embed(self, name, title, description, color):
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_author(name=name, icon_url=self.me.avatar_url)
        embed.set_footer(text=res.get("messages.embed_footer"), icon_url=self.me.avatar_url)
        return embed

    def extension_idx(self, ext: Any) -> None:
        pass

    ################
    # Sync methods #
    ################

    def run(self) -> None:
        super().run(self.token)

    def check_config(self) -> None:
        log.info(f'Checking configuration')
        for i, role_name in enumerate(self.config.control.roles):
            if self.get_role(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", self.config.control.path(f'roles[{i}]'))

    def save_config(self):
        log.info(f'Saving configuration on disk')
        self.cnf_manager.save()

    def set_awaiting_sync(self) -> None:
        self.__awaiting_sync_last_updated = datetime.now()
        self.__awaiting_sync = True

    def unset_awaiting_sync(self) -> None:
        self.__awaiting_sync_last_updated = datetime.now()
        self.__awaiting_sync = False

    def extend(self, extension: Any) -> None:
        pass

    def update_command_cache(self) -> None:
        pass

    def resolve_extension(self, ext: Union[int, str]) -> Optional[Any]:
        pass

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
        await self.maintainer.send(res.get("messages.error").format(msg))
        return

    async def sync_users(self) -> None:
        log.info('Syncing roles')
        self.s_roles.load(self.guild.roles)
        log.info(f'Syncing users')
        self.s_users.mark_everyone_absent()
        async for member in self.guild.fetch_members(limit=None):
            if member.bot:
                continue
            # Update and repair
            user = self.s_users.update_member(member)
            self.s_events.repair_member_joined_event(member, user)
        # Remove effectively absent
        if not self.config["user.leave.keep"]:
            self.s_users.remove_absent()
        self.unset_awaiting_sync()
        log.info(f'Syncing is done')

    async def resolve_user(self, user_mention: str) -> Optional[discord.User]:
            try:
                if '#' in user_mention:
                    user = self.s_users.get_by_qualified_name(user_mention)
                elif user_mention.startswith('<@'):
                    id = int(user_mention[2:-1])
                    return await self.fetch_user(id)
                else:
                    user = self.s_users.get_by_display_name(user_mention)
                if user is None:
                    return None
                return await self.fetch_user(user.did)
            except discord.NotFound:
                return None
            except ValueError:
                return None

    async def resolve_text_channel(self, channel_mention: str) -> Optional[discord.TextChannel]:
            if '<' in channel_mention:
                channel = [c for c in self.guild.text_channels if c.mention == channel_mention]
                return channel[0] if channel else None
            if '#' in channel_mention:
                channel_name = channel_mention[1:]
            else:
                channel_name = channel_mention
            channel = [c for c in self.guild.text_channels if c.name == channel_name]
            return channel[0] if channel else None

    async def resolve_voice_channel(self, channel_mention: str) -> Optional[discord.VoiceChannel]:
            if '<' in channel_mention:
                channel = [c for c in self.guild.voice_channels if c.mention == channel_mention]
                return channel[0] if channel else None
            if '#' in channel_mention:
                channel_name = channel_mention[1:]
            else:
                channel_name = channel_mention
            channel = [c for c in self.guild.voice_channels if c.name == channel_name]
            return channel[0] if channel else None

    async def resolve_member_w_fb(self, user_mention: str, fb_channel: discord.TextChannel) -> Optional[discord.Member]:
        user = await self.resolve_user(user_mention)
        if user is None:
            await fb_channel.send(res.get("messages.unknown_user"))
            return
        try:
            member = await self.guild.fetch_member(user.id)
        except discord.NotFound:
            await fb_channel.send(res.get("messages.not_member_user"))
            return
        return member

    async def logout(self) -> None:
        await super().logout()

    async def alter_config(self, config: str) -> None:
        log.info(f'Altering configuration')
        self.cnf_manager.alter(config)
        self.config = self.cnf_manager.find_section(OverlordRootConfig)
        await self.on_config_update()

    async def safe_alter_config(self, config: str) -> Optional[Exception]:
        old_config = self.cnf_manager.raw
        try:
            await self.alter_config(config)
        except (InvalidConfigException, TypeError) as e:
            log.warn(f'Invalid config data: {e}. Reverting.')
            await self.alter_config(old_config)
            return e
        return None

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
        exception_tb_limited = limit_traceback(exception_tb, "src", 6)
        exception_tb_quoted = quote_msg('\n'.join(exception_tb_limited))

        exception_msg = res.get("messages.dm_bot_exception").format(event, ('`'+str(ex).replace("`","\\`")+'`')) + '\n' + exception_tb_quoted

        exception_msg_short = f'`{str(ex)}` Reported to {self.maintainer.mention}'

        if self.error_channel is not None and event != 'on_ready':
            await self.error_channel.send(res.get("messages.error").format(exception_msg_short))
        
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
            self.maintainer = await self.guild.fetch_member(self.maintainer_id)
            await self.maintainer.send('Starting instance')
        except discord.NotFound:
            raise InvalidConfigException(f'Error maintainer id is invalid', 'MAINTAINER_DISCORD_ID')
        except discord.Forbidden:
            raise InvalidConfigException(f'Error cannot send messagees to maintainer', 'MAINTAINER_DISCORD_ID')
        log.info(f'Maintainer is {qualified_name(self.maintainer)} ({self.maintainer.id})')

        # Sync roles and users
        await self.sync_users()

        # Check config value
        await self.on_config_update()

        self.__initialized = True
        
    async def on_config_update(self) -> None:
        self.check_config()
        self.update_command_cache()
