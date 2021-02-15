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
from typing import Dict, List, Callable, Awaitable, Optional, Union

import discord

import db as DB
from extensions import BotExtension
from util import get_coroutine_attrs, parse_control_message
from util.config import ConfigManager
from util.exceptions import InvalidConfigException
from util.extbot import qualified_name, is_dm_message
from util.extbot import skip_bots, after_initialized, guild_member_event
from util.resources import R
from .base import OverlordBase
from .types import OverlordMessageDelete, OverlordMember, OverlordMessage, OverlordMessageEdit, OverlordReaction, \
    OverlordRole, OverlordVCState

log = logging.getLogger('overlord-bot')


#############################
# Main class implementation #
#############################

class Overlord(OverlordBase):
    # Extensions
    _extensions: List[BotExtension]
    _handlers: Dict[str, Callable[..., Awaitable[None]]]
    _call_plan_map: Dict[str, List[List[Callable[..., Awaitable[None]]]]]
    _cmd_cache: Dict[str, Callable[..., Awaitable[None]]]

    def __init__(self, cnf_manager: ConfigManager, db_session: DB.DBPersistSession) -> None:
        super().__init__(cnf_manager, db_session)
        self._extensions = []
        handlers = get_coroutine_attrs(self, name_filter=lambda x: x.startswith('on_'))
        self._handlers = {n.replace('_raw', ''): h for n, h in handlers.items()}
        self._call_plan_map = {}
        self._cmd_cache = {}

    ################
    # Sync methods #
    ################

    @property
    def extensions(self) -> List[BotExtension]:
        return self._extensions

    def extend(self, extension: BotExtension) -> None:
        self._extensions.append(extension)
        self._extensions.sort(key=lambda e: e.priority)
        self._call_plan_map = {}
        for h in self._handlers:
            self._build_call_plan(h)

    def _build_call_plan(self, handler_name) -> None:
        if handler_name == 'on_error':
            return
        # Build call plan
        call_plan = [[] for _ in range(64)]
        for extension in self._extensions:
            if not hasattr(extension, handler_name):
                continue
            call_plan[extension.priority].append(getattr(extension, handler_name))
        self._call_plan_map[handler_name] = [call for call in call_plan if call]

    def _find_cmd_handler(self, name: str) -> Callable[..., Awaitable[None]]:
        for ext in self._extensions:
            handler = ext.cmd_handler(name)
            if handler is not None:
                return handler
        raise InvalidConfigException(f"Command handler not found for {name}", "bot.commands")

    def update_command_cache(self) -> None:
        self._cmd_cache = {}
        for cmd, aliases in self.config.command.items():
            handler = self._find_cmd_handler(cmd)
            for alias in aliases:
                if alias in self._cmd_cache:
                    raise InvalidConfigException(f"Command alias collision for {alias}: {cmd}", "bot.commands")
                self._cmd_cache[alias] = handler

    def resolve_extension(self, ext: Union[int, str]) -> Optional[BotExtension]:
        if isinstance(ext, int):
            if 0 < ext <= len(self._extensions):
                return self._extensions[ext - 1]
            return None
        try:
            return self.resolve_extension(int(ext))
        except ValueError:
            search = [e for e in self._extensions if e.name == ext]
            return search[0] if search else None

    def extension_idx(self, ext: BotExtension) -> int:
        for i in range(len(self._extensions)):
            if self._extensions[i] is ext:
                return i
        return -1

    #################
    # Async methods #
    #################

    async def _run_call_plan(self, name: str, *args, **kwargs) -> None:
        call_plan = self._call_plan_map[name]
        for handlers in call_plan:
            calls = [h(*args, **kwargs) for h in handlers]
            await asyncio.gather(*calls)

    async def logout(self) -> None:
        for ext in self._extensions:
            ext.stop()
        return await super().logout()

    #########
    # Hooks #
    #########

    async def on_ready(self) -> None:
        async with self.sync():
            await super().on_ready()
            # Start extensions
            for ext in self._extensions:
                ext.start()
            # Call 'on_ready' extension handlers
            await self._run_call_plan('on_ready')
            # Check config value
            await self.on_config_update()
            # Message for pterodactyl panel
            print(self.config.egg_done)
            start_report = f'{R.NAME.COMMON.GUILD}: {self.guild.name}\n'
            start_report += f'{R.NAME.COMMON.MAINTAINER}: {self.maintainer.mention}\n'
            start_report += f'{R.NAME.COMMON.CONTROL_CHANNEL}: {self.control_channel.mention}\n'
            if self.error_channel is not None:
                start_report += f'{R.NAME.COMMON.ERROR_CHANNEL}: {self.error_channel.mention}\n'
            embed = self.new_info_report(R.MESSAGE.STATUS.STARTED, start_report)
            await self.maintainer.send(embed=embed)

    async def on_config_update(self) -> None:
        await super().on_config_update()
        # Call extension 'on_config_update' handlers
        await self._run_call_plan('on_config_update')

    @after_initialized
    @skip_bots
    async def on_message(self, message: discord.Message) -> None:
        """
            Async new message event handler

            Saves event in database
        """
        # handle control commands separately
        if message.channel == self.control_channel or (message.author == self.maintainer and is_dm_message(message)):
            await self._on_control_message(message)
            return
        if not self.is_guild_member_message(message):
            return
        async with self.sync():
            user = self.s_users.get(message.author)
            # Skip non-existing users
            if user is None:
                log.warning(f'{qualified_name(message.author)} does not exist in db! Skipping new message event!')
                return
            # Save event
            msg = self.s_events.create_new_message_event(user, message)
        # Call extension 'on_message' handlers
        await self._run_call_plan('on_message', OverlordMessage(message, msg))

    async def _on_control_message(self, message: discord.Message) -> None:
        """
            Async new control message event handler

            Calls appropriate control callback
        """
        # Filter non-admins
        if not self.is_admin(message.author):
            return
        # Parse argv
        argv = parse_control_message(self.prefix, message)
        if argv is None or len(argv) == 0:
            return
        # Resolve cmd handler
        cmd_name = argv[0]
        if cmd_name not in self._cmd_cache:
            await message.channel.send(R.MESSAGE.ERROR.UNKNOWN_COMMAND)
            return
        handler = self._cmd_cache[cmd_name]
        # Call handler
        await handler(message, self.prefix, argv)

    @after_initialized
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        """
            Async message edit event handler

            Saves event in database
        """
        if self.is_special_channel_id(payload.channel_id):
            return
        async with self.sync():
            # ignore absent
            msg = self.s_events.get_message(payload.message_id)
            if msg is None:
                return
            # Save event
            msg_edit = self.s_events.create_message_edit_event(msg)
        # Call extension 'on_message_edit' handlers
        await self._run_call_plan('on_message_edit', OverlordMessageEdit(payload, msg_edit))

    @after_initialized
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """
            Async message delete event handler

            Saves event in database
        """
        if self.is_special_channel_id(payload.channel_id):
            return
        async with self.sync():
            # ignore absent
            msg = self.s_events.get_message(payload.message_id)
            if msg is None:
                return
            # Save event
            msg_delete = self.s_events.create_message_delete_event(msg)
        # Call extension 'on_message_delete' handlers
        await self._run_call_plan('on_message_delete', OverlordMessageDelete(payload, msg_delete))

    @after_initialized
    @skip_bots
    @guild_member_event
    async def on_member_join(self, member: discord.Member) -> None:
        """
            Async member join event handler

            Saves user in database
        """
        async with self.sync():
            # Add/update user
            user = self.s_users.update_member(member)
            # Save event
            self.s_events.create_member_join_event(user, member)
        # Call extension 'on_member_join' handlers
        await self._run_call_plan('on_member_join', OverlordMember(member, user))

    @after_initialized
    @skip_bots
    @guild_member_event
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """
            Async member remove event handler

            Removes user from database (or keep it, depends on config)
        """
        # track only role/nickname change
        if not (before.roles != after.roles or
                before.display_name != after.display_name or
                before.name != after.name or
                before.discriminator != after.discriminator):
            return
        async with self.sync():
            # Skip absent
            user = self.s_users.get(before)
            if user is None:
                log.warning(f'{qualified_name(after)} does not exist in db! Skipping user update event!')
                return
            # Update user
            self.s_users.update_member(after)
        # Call extension 'on_member_update' handlers
        await self._run_call_plan('on_member_update', OverlordMember(before, user), OverlordMember(after, user))

    @after_initialized
    @skip_bots
    @guild_member_event
    async def on_member_remove(self, member: discord.Member) -> None:
        """
            Async member remove event handler

            Removes user from database (or keep it, depends on config)
        """
        async with self.sync():
            if self.config.keep_absent_users:
                user = self.s_users.mark_absent(member)
                if user is None:
                    log.warning(f'{qualified_name(member)} does not exist in db! Skipping user leave event!')
                    return
                self.s_events.create_user_leave_event(user)
            else:
                user = self.s_users.remove(member)
                if user is None:
                    log.warning(f'{qualified_name(member)} does not exist in db! Skipping user leave event!')
                    return
        # Call extension 'on_member_remove' handlers
        await self._run_call_plan('on_member_remove', OverlordMember(member, user))

    @after_initialized
    @skip_bots
    @guild_member_event
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
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

    @after_initialized
    async def on_vc_join(self, member: discord.Member, state: discord.VoiceState) -> None:
        """
            Async vc join event handler

            Saves event in database
        """
        async with self.sync():
            user = self.s_users.get(member)
            # Skip non-existing users
            if user is None:
                log.warning(f'{qualified_name(member)} does not exist in db! Skipping vc join event!')
                return
            # Apply constraints
            self.s_events.repair_vc_leave_event(user, state.channel)
            # Save event
            event = self.s_events.create_vc_join_event(user, state.channel)
        # Call extension 'on_vc_join' handlers
        await self._run_call_plan('on_vc_join', OverlordMember(member, user), OverlordVCState(state, event))

    @after_initialized
    async def on_vc_leave(self, member: discord.Member, state: discord.VoiceState) -> None:
        """
            Async vc join event handler

            Saves event in database
        """
        async with self.sync():
            user = self.s_users.get(member)
            # Skip non-existing users
            if user is None:
                log.warning(f'{qualified_name(member)} does not exist in db! Skipping vc leave event!')
                return
            # Close event
            events = self.s_events.close_vc_join_event(user, state.channel)
            if events is None:
                return
            join_event, leave_event = events
        # Call extension 'on_vc_leave' handlers
        await self._run_call_plan('on_vc_leave', OverlordMember(member, user), OverlordVCState(state, join_event),
                                  OverlordVCState(state, leave_event))

    @after_initialized
    async def on_guild_role_create(self, role: discord.Role) -> None:
        """
            Async guild role create event handler

            Saves event in database
        """
        async with self.sync():
            await self.sync_users()
        # Call extension 'on_guild_role_create' handlers
        await self._run_call_plan('on_guild_role_create', OverlordRole(role, self.s_roles.get(role.name)))

    @after_initialized
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        """
            Async guild role delete event handler

            Saves event in database
        """
        async with self.sync():
            await self.sync_users()
        # Call extension 'on_guild_role_delete' handlers
        await self._run_call_plan('on_guild_role_delete', OverlordRole(role, self.s_roles.get(role.name)))

    @after_initialized
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        """
            Async guild role update event handler

            Saves event in database
        """
        async with self.sync():
            await self.sync_users()
        role = self.s_roles.get(before.name)
        # Call extension 'on_guild_role_update' handlers
        await self._run_call_plan('on_guild_role_update', OverlordRole(before, role), OverlordRole(after, role))

    @after_initialized
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """
            Async new reaction event handler

            Saves event in database
        """
        async with self.sync():
            try:
                # Resolve member, channel, message
                member = await self.guild.fetch_member(payload.user_id)
                channel = await self.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
            except discord.NotFound:
                return
            if member.bot:
                return
            # handle control reactions
            if channel == self.control_channel or (
                    member == self.maintainer and isinstance(channel, discord.DMChannel)):
                await self.on_control_reaction_add(member, message, payload.emoji)
                return
            if not self.is_guild_member_message(message):
                return
            # ignore absent
            msg = self.s_events.get_message(message.id)
            if msg is None:
                return
            user = self.s_users.get(member)
            if user is None:
                log.warning(f'{qualified_name(message.author)} does not exist in db! Skipping new reaction event!')
                return
            # Save event
            event = self.s_events.create_new_reaction_event(user, msg)
        # Call extension 'on_reaction_add' handlers
        await self._run_call_plan('on_reaction_add', OverlordMember(member, user), OverlordMessage(message, msg),
                                  OverlordReaction(payload.emoji, event))

    async def on_control_reaction_add(self, member: discord.Member, message: discord.Message,
                                      emoji: discord.PartialEmoji) -> None:
        """
            Async control reaction add event handler

            Saves event in database
        """
        # Call extension 'on_control_reaction_add' handlers
        await self._run_call_plan('on_control_reaction_add', member, message, emoji)

    @after_initialized
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """
            Async reaction remove event handler

            Saves event in database
        """
        async with self.sync():
            try:
                # Resolve member, channel, message
                member = await self.guild.fetch_member(payload.user_id)
                channel = await self.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
            except discord.NotFound:
                return
            if member.bot:
                return
            # handle control reactions
            if channel == self.control_channel or (
                    member == self.maintainer and isinstance(channel, discord.DMChannel)):
                await self.on_control_reaction_remove(member, message, payload.emoji)
                return
            if not self.is_guild_member_message(message):
                return
            # ignore absent
            msg = self.s_events.get_message(message.id)
            if msg is None:
                return
            user = self.s_users.get(member)
            if user is None:
                log.warning(f'{qualified_name(message.author)} does not exist in db! Skipping new reaction event!')
                return
            # Save event
            event = self.s_events.create_reaction_delete_event(user, msg)
        # Call extension 'on_reaction_remove' handlers
        await self._run_call_plan('on_reaction_remove', OverlordMember(member, user), OverlordMessage(message, msg),
                                  OverlordReaction(payload.emoji, event))

    async def on_control_reaction_remove(self, member: discord.Member, message: discord.Message,
                                         emoji: discord.PartialEmoji) -> None:
        """
            Async control reaction add event handler

            Saves event in database
        """
        # Call extension 'on_control_reaction_add' handlers
        await self._run_call_plan('on_control_reaction_remove', member, message, emoji)
