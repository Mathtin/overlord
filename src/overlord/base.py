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
import os
import sys
import traceback
from typing import Any, List, Optional, Union

import discord

import src.db as DB
from src.services import EventService, RoleService, StatService, UserService
from src.util import limit_traceback
from src.util.config import ConfigManager
from src.util.exceptions import InvalidConfigException, NotCoroutineException
from src.util.extbot import is_dm_message, filter_roles, is_text_channel, qualified_name
from src.util.logger import DiscordLogConfig
from src.util.resources import R
from .types import OverlordRootConfig

log = logging.getLogger('overlord-bot')


#############################
# Base class implementation #
#############################

class OverlordBase(discord.Client):
    _async_lock: asyncio.locks
    _initialized: bool

    # Members loaded from ENV
    token: str
    guild_id: int
    control_channel_id: int
    error_channel_id: int
    maintainer_id: int

    # Members passed via constructor
    cnf_manager: ConfigManager
    config: OverlordRootConfig
    log_config: DiscordLogConfig
    db: DB.DBPersistSession

    # Values initiated on_ready
    guild: discord.Guild
    control_channel: discord.TextChannel
    error_channel: Optional[discord.TextChannel]
    maintainer: discord.Member
    me: discord.Member

    # Services
    s_users: UserService
    s_roles: RoleService
    s_events: EventService
    s_stats: StatService

    def __init__(self, cnf_manager: ConfigManager, db_session: DB.DBPersistSession) -> None:
        # Internal fields
        self._async_lock = asyncio.Lock()
        self._initialized = False
        self.error_channel = None

        # User supplied fields
        self.cnf_manager = cnf_manager
        self.reload_sections()
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
        raise NotImplementedError()

    @property
    def prefix(self) -> str:
        return self.config.control.prefix

    def sync(self) -> asyncio.Lock:
        return self._async_lock

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

    def extension_idx(self, ext: Any) -> int:
        raise NotImplementedError()

    def get_config_section(self, section_type: Any) -> Any:
        return self.cnf_manager.find_section(section_type)

    ##########
    # Embeds #
    ##########

    def new_embed(self, title, body, footer: str = None, header: str = None, color: int = 0xd75242):
        header = header or R.EMBED.HEADER.DEFAULT
        footer = footer or R.EMBED.FOOTER.DEFAULT
        embed = discord.Embed(title=title, description=body, color=color)
        embed.set_author(name=header, icon_url=self.me.avatar_url)
        embed.set_footer(text=footer, icon_url=self.me.avatar_url)
        return embed

    def new_error_report(self, name: str, details: str, traceback_: Optional[List[str]] = None, color: int = 0xd75242):
        header = R.EMBED.HEADER.ERROR_REPORT
        title = f'❗ {name}'
        embed = self.new_embed(title=title, body=details, header=header, color=color)
        if traceback_ is not None:
            traceback_limited = limit_traceback(traceback_, "src", 6)
            embed.add_field(name=R.NAME.COMMON.TRACEBACK, value='\n'.join(traceback_limited), inline=False)
        return embed

    def new_warn_report(self, name: str, details: str, color: int = 0xd75242):
        header = R.EMBED.HEADER.WARN_REPORT
        title = f'⚠ {name}'
        embed = self.new_embed(title=title, body=details, header=header, color=color)
        return embed

    def new_info_report(self, name: str, details: str, color: int = 0xd75242):
        header = R.EMBED.HEADER.INFO_REPORT
        title = f'📰 {name}'
        embed = self.new_embed(title=title, body=details, header=header, color=color)
        return embed

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

    def extend(self, extension: Any) -> None:
        pass

    def update_command_cache(self) -> None:
        pass

    def resolve_extension(self, ext: Union[int, str]) -> Optional[Any]:
        pass

    def save_config(self) -> None:
        log.info(f'Saving configuration on disk')
        self.cnf_manager.save()

    def reload_sections(self) -> None:
        self.config = self.get_config_section(OverlordRootConfig)
        if self.config is None:
            raise InvalidConfigException("OverlordRootConfig section not found", "root")
        self.log_config = self.get_config_section(DiscordLogConfig)
        if self.log_config is None:
            raise InvalidConfigException("DiscordLogConfig section not found", "root")

    #################
    # Async methods #
    #################

    async def init_lock(self) -> None:
        while not self._initialized:
            await asyncio.sleep(0.1)
        return

    async def send_error(self, from_: str, msg: str) -> None:
        error_report = self.new_error_report(from_, msg)
        if self.error_channel is not None:
            await self.error_channel.send(embed=error_report)
        await self.maintainer.send(embed=error_report)
        return

    async def send_warning(self, from_: str, msg: str) -> None:
        warn_report = self.new_warn_report(from_, msg)
        if self.error_channel is not None:
            await self.error_channel.send(embed=warn_report)
        await self.maintainer.send(embed=warn_report)
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
        if not self.config.keep_absent_users:
            self.s_users.remove_absent()
        log.info(f'Syncing is done')

    async def resolve_user(self, user_mention: str) -> Optional[discord.User]:
        try:
            if '#' in user_mention:
                user = self.s_users.get_by_qualified_name(user_mention)
            elif user_mention.startswith('<@'):
                return await self.fetch_user(int(user_mention[2:-1]))
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

    async def logout(self) -> None:
        await super().logout()

    async def alter_config(self, config: str) -> None:
        log.info(f'Altering configuration')
        self.cnf_manager.alter(config)
        self.reload_sections()
        await self.on_config_update()

    async def safe_alter_config(self, config: str) -> Optional[Exception]:
        old_config = self.cnf_manager.raw
        try:
            await self.alter_config(config)
        except (InvalidConfigException, TypeError) as e:
            log.warning(f'Invalid config data: {e}. Reverting.')
            await self.alter_config(old_config)
            return e
        return None

    async def update_config(self) -> None:
        log.info(f'Updating configuration')
        self.save_config()
        self.reload_sections()
        await self.on_config_update()

    async def safe_update_config(self) -> Optional[Exception]:
        old_config = self.cnf_manager.raw
        try:
            await self.update_config()
        except (InvalidConfigException, TypeError) as e:
            log.warning(f'Invalid config data. Reverting.')
            await self.alter_config(old_config)
            return e
        return None

    async def reload_config(self) -> None:
        log.info(f'Altering configuration')
        self.cnf_manager.reload()
        self.reload_sections()
        await self.on_config_update()

    #########
    # Hooks #
    #########

    async def on_error(self, event, *args, **kwargs) -> None:
        """
            Async error event handler

            Sends stacktrace to error channel
        """
        logging.exception(f'Error on event: {event}')

        ex_type = sys.exc_info()[0]
        ex = sys.exc_info()[1]
        tb = traceback.format_exception(*sys.exc_info())
        name = ex_type.__name__

        reported_to = f'{R.MESSAGE.STATUS.REPORTED_TO} {self.maintainer.mention}'

        maintainer_report = self.new_error_report(name, str(ex), tb)
        channel_report = self.new_error_report(name, str(ex) + '\n' + reported_to)

        if self.error_channel is not None and event != 'on_ready':
            await self.error_channel.send(embed=channel_report)

        await self.maintainer.send(embed=maintainer_report)

        if ex_type is InvalidConfigException:
            await self.logout()
        if ex_type is NotCoroutineException:
            await self.logout()
        if event == 'on_ready':
            await self.logout()

    async def on_ready(self) -> None:
        """
            Async ready event handler

            Completely initialize bot state
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
            raise InvalidConfigException(f"{channel.name}({channel.id}) is not text channel", 'DISCORD_CONTROL_CHANNEL')
        log.info(f'Attached to {channel.name} as control channel ({channel.id})')
        self.control_channel = channel

        # Attach error channel
        if self.error_channel_id:
            channel = self.get_channel(self.error_channel_id)
            if channel is None:
                raise InvalidConfigException(f'Error channel id is invalid', 'DISCORD_ERROR_CHANNEL')
            if not is_text_channel(channel):
                raise InvalidConfigException(f"{channel.name}({channel.id}) is not text channel",
                                             'DISCORD_ERROR_CHANNEL')
            log.info(f'Attached to {channel.name} as error channel ({channel.id})')
            self.error_channel = channel

        # Resolve maintainer
        try:
            self.maintainer = await self.guild.fetch_member(self.maintainer_id)
        except discord.NotFound:
            raise InvalidConfigException(f'Error maintainer id is invalid', 'MAINTAINER_DISCORD_ID')
        except discord.Forbidden:
            raise InvalidConfigException(f'Error cannot send messages to maintainer', 'MAINTAINER_DISCORD_ID')
        log.info(f'Maintainer is {qualified_name(self.maintainer)} ({self.maintainer.id})')

        # Sync roles and users
        await self.sync_users()

        self._initialized = True

    async def on_config_update(self) -> None:
        self.check_config()
        self.update_command_cache()
