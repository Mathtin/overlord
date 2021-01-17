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

import asyncio
import logging

import discord
import db as DB
import util.resources as res

from util import ConfigView, get_coroutine_attrs, parse_control_message
from util.exceptions import InvalidConfigException
from util.extbot import qualified_name, is_dm_message
from util.extbot import skip_bots, after_initialized, event_config, guild_member_event
from typing import Dict, List, Callable, Awaitable, Optional, Union
from .base import OverlordBase
from .types import OverlordMessageDelete, OverlordMember, OverlordMessage, OverlordMessageEdit, OverlordRole, OverlordUser, OverlordVCState
from extensions.base import BotExtension

log = logging.getLogger('overlord-bot')

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

    ################
    # Sync methods #
    ################

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

    def resolve_extension(self, ext: Union[int, str]) -> Optional[BotExtension]:
        if isinstance(ext, int):
            if 0 < ext <= len(self.__extensions):
                return self.__extensions[ext-1]
            return None
        try:
            return self.resolve_extension(int(ext))
        except ValueError:
            exts = [e for e in self.__extensions if e.name == ext]
            return exts[0] if exts else None

    def extension_idx(self, ext: BotExtension) -> int:
        for i in range(len(self.__extensions)):
            if self.__extensions[i] is ext:
                return i
        return -1

    #################
    # Async methods #
    #################

    async def __run_call_plan(self, name: str, *args, **kwargs) -> None:
        call_plan = self.__call_plan_map[name]
        for handlers in call_plan:
            calls = [h(*args, **kwargs) for h in handlers]
            await asyncio.wait(calls)

    async def logout(self) -> None:
        for ext in self.__extensions:
            ext.stop()
        return await super().logout()
        
    async def update_config(self, config: ConfigView) -> None:
        await super().update_config(config)
        self.update_command_cache()
        await self.on_config_update()

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

    async def on_config_update(self) -> None:
        self.check_config()
        # Call extension 'on_config_update' handlers
        await self.__run_call_plan('on_config_update')

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
        argv = parse_control_message(self.prefix, message)
        if argv is None or len(argv) == 0:
            return
        # Resolve cmd handler
        cmd_name = argv[0]

        # Handle help page
        if cmd_name == 'help':
            page = argv[1] if len(argv) > 1 else 0
            ext = self.resolve_extension(page)
            if ext is None:
                await message.channel.send("No such help page")
                return
            i = self.extension_idx(ext)
            l = len(self.__extensions)
            await message.channel.send(embed=ext.help_embed(f"Overlord Help page [{i+1}/{l}]"))
            return

        if cmd_name not in self.__cmd_cache:
            await message.channel.send(res.get("messages.unknown_command"))
            return
        handler = self.__cmd_cache[cmd_name]
        # Call handler
        await handler(message, self.prefix, argv)

    
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
