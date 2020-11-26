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
import db
import db.queries as q
import db.converters as conv

from util import *
import util.resources as res
from typing import Optional

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
        if isinstance(obj, discord.User):
            if self.is_bot(obj):
                return
        elif isinstance(obj, discord.Message): 
            if self.is_bot_message(obj):
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

    # Members loaded from ENV
    token: str
    guild_id: int
    control_channel_id: int
    error_channel_id: int

    # Members passed via constructor
    config: ConfigView
    db: db.DBSession

    # Maps name -> id (gathered via db)
    event_type_map: dict
    user_stat_type_map: dict

    # Values initiated on_ready
    guild: discord.Guild
    control_channel: discord.TextChannel
    error_channel: discord.TextChannel
    role_map: dict
    commands: dict
    bot_members: dict

    def __init__(self, config: ConfigView, db_session: db.DBSession):
        self.__async_lock = asyncio.Lock()
        self.__initialized = False
        self.__awaiting_role_sync = True
        self.__awaiting_user_sync = True

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
        self.event_type_map = {row.name:row.id for row in self.db.query(db.EventType)}
        self.user_stat_type_map = {row.name:row.id for row in self.db.query(db.UserStatType)}

        # Preset some values initiated on_ready
        self.commands = {}
        self.bot_members = {}

    ###########
    # Getters #
    ###########

    def event_type_id(self, name):
        return self.event_type_map[name]

    def user_stat_type_id(self, name):
        return self.user_stat_type_map[name]

    def sync(self):
        return self.__async_lock

    def is_bot_message(self, msg: discord.Message) -> bool:
        return msg.author.id in self.bot_members

    def is_bot(self, user: discord.User) -> bool:
        if user.bot:
            self.bot_members[user.id] = user
        return user.bot

    def is_guild_member(self, member: discord.Member) -> bool:
        return member.guild.id == self.guild.id

    def is_guild_member_message(self, msg: discord.Message) -> bool:
        return not is_dm_message(msg) and msg.guild.id == self.guild.id

    def check_afk_state(self, state: discord.VoiceState) -> bool:
        return not state.afk or not self.config["event.voice.afk.ignore"]

    def is_special_channel_id(self, channel_id: int):
        return channel_id == self.control_channel.id or channel_id == self.error_channel.id

    def get_user_stat(self, user: db.User, stat_name: str):
        stat = q.get_user_stat_by_id(self.db, user.id, self.user_stat_type_map[stat_name])
        return stat.value if stat is not None else 0

    def can_apply_rank(self, user: db.User, rank: ConfigView):
        messages = self.get_user_stat(user, "new_message_count") - self.get_user_stat(user, "delete_message_count")
        vc_time = self.get_user_stat(user, "vc_time")
        return messages >= rank["messages"] and vc_time >= rank["vc"]

    def get_member_rank_roles(self, member: discord.Member) -> Optional[str]:
        res = []
        for rank_name in self.config.role.ranks:
            if is_role_applied(member, rank_name):
                res.append(rank_name)
        return res

    def get_role(self, role_name: str):
        for r in self.guild.roles:
            if r.name == role_name:
                return r
        return None

    def is_admin(self, user: discord.Member):
        roles = self.config["role.admin"]
        return len(filter_roles(user, roles)) > 0

    ################
    # Sync methods #
    ################

    def run(self):
        super().run(self.token)

    def find_user_rank(self, user: db.User) -> Optional[str]:
        ranks = self.config["role.ranks"]
        max_rank = {"weight": -1000}
        max_rank_name = None
        for rank_name in ranks:
            rank = ConfigView(value=ranks[rank_name], schema_name="rank_schema")
            if self.can_apply_rank(user, rank) and max_rank["weight"] < rank["weight"]:
                max_rank = rank
                max_rank_name = rank_name
        return max_rank_name

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

    async def send_warning(self, msg: str):
        if self.error_channel is not None:
            await self.error_channel.send(res.get("messages.warning").format(msg))
        return

    async def sync_roles(self):
        log.info('Syncing roles')
        roles = conv.roles_to_rows(self.guild.roles)
        self.role_map = { role['did']: role for role in roles }
        self.db.sync_table(db.Role, 'did', roles)
        self.db.commit()
        self.__awaiting_role_sync = False
        log.info('Syncing roles done')

    async def sync_users(self):
        if self.__awaiting_role_sync:
            log.error(f'Cannot sync users: awaiting role sync')
            await self.send_error(f'Cannot sync users: awaiting role sync')
            return
        log.info(f'Syncing users')
        async for member in self.guild.fetch_members(limit=None):
            # Skip bots
            if member.bot:
                self.bot_members[member.id] = member
                continue
            # Update user
            u_row = conv.member_row(member, self.role_map)
            user = self.db.update_or_add(db.User, 'did', u_row)
            self.db.commit()
            # Check and repair last member event (should be join)
            last_event = q.get_last_member_event_by_did(self.db, user.did)
            if last_event is None or last_event.type_id != self.event_type_id("member_join"):
                e_row = conv.member_join_row(user, member.joined_at, self.event_type_map)
                self.db.add(db.MemberEvent, e_row)
            self.db.commit()
        self.__awaiting_user_sync = False
        log.info(f'Syncing users done')

    async def update_user_rank(self, user: db.User, member: discord.Member):
        if self.__awaiting_role_sync:
            log.error("Cannot update user rank: awaiting role sync")
            await self.send_error(f'Cannot update user rank: awaiting role sync')
            return
        if self.is_admin(member):
            return
        # Resolve user rank
        rank_name = self.find_user_rank(user)
        if rank_name is None:
            return
        log.debug(f"Updating {qualified_name(member)}'s rank: {rank_name}'")
        if is_role_applied(member, rank_name):
            log.debug(f"No updating required")
            return
        # Get and remove already applied ranks
        applied_rank_roles = self.get_member_rank_roles(member)
        if applied_rank_roles:
            applied_rank_names = ', '.join([r.name for r in applied_rank_roles])
            log.info(f"Removing {qualified_name(member)}'s rank roles: {applied_rank_names}")
            await member.remove_roles(*applied_rank_roles)
        # Apply new rank
        log.info(f"Adding rank role to {qualified_name(member)}: {rank_name}")
        await member.add_roles(self.get_role(rank_name))
        # Update user in db
        u_row = conv.member_row(member, self.role_map)
        user = self.db.update(db.User, 'did', u_row)
        self.db.commit()

    async def update_user_ranks(self):
        if self.__awaiting_role_sync:
            log.error("Cannot update user ranks: awaiting role sync")
            await self.send_error(f'Cannot update user ranks: awaiting role sync')
            return
        log.info(f'Updating user ranks')
        async for member in self.guild.fetch_members(limit=None):
            # Skip bots
            if member.bot:
                self.bot_members[member.id] = member
                continue
            user = q.get_user_by_did(self.db, member.id)
            # Skip non-existing users
            if user is None:
                log.warn(f'{qualified_name(member)} does not exist in db! Skipping user rank update!')
                continue
            await self.update_user_rank(user, member)
        log.info(f'Done updating user ranks')

    #########
    # Hooks #
    #########

    async def on_error(self, event, *args, **kwargs):
        """
            Async error event handler

            Sends stacktrace to error channel
        """
        ex_type = sys.exc_info()[0]

        logging.exception(f'Error on event: {event}')

        exception_lines = traceback.format_exception(*sys.exc_info())

        exception_msg = '`' + ''.join(exception_lines).replace('`', '\'')[:1000] + '`'

        if self.error_channel is not None:
            await self.error_channel.send(exception_msg)

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

            # Attach control channel
            channel = self.get_channel(self.control_channel_id)
            if channel is None:
                raise InvalidConfigException(f'Control channel id is invalid', 'DISCORD_CONTROL_CHANNEL')
            if not is_text_channel(channel):
                raise InvalidConfigException(f"{channel.name}({channel.id}) is not text channel",'DISCORD_CONTROL_CHANNEL')
            log.info(f'Attached to {channel.name} as control channel ({channel.id})')
            self.control_channel = channel

            # Attach error channel
            if self.error_channel_id is not None:
                channel = self.get_channel(self.error_channel_id)
                if channel is None:
                    raise InvalidConfigException(f'Error channel id is invalid', 'DISCORD_ERROR_CHANNEL')
                if not is_text_channel(channel):
                    raise InvalidConfigException(f"{channel.name}({channel.id}) is not text channel",'DISCORD_ERROR_CHANNEL')
                log.info(f'Attached to {channel.name} as error channel ({channel.id})')
                self.error_channel = channel

            # Attach control hooks
            control_hooks = self.config["commands"]
            for cmd in control_hooks:
                hook = get_module_element(control_hooks[cmd])
                check_coroutine(hook)
                self.commands[cmd] = hook

            # Check ranks config
            ranks = self.config["role.ranks"]
            for rank_name in ranks:
                _ = ConfigView(value=ranks[rank_name], schema_name="rank_schema")
                if self.get_role(rank_name) is None:
                    raise InvalidConfigException("Bad role name", "bot.role.ranks")

            # Sync roles and users
            await self.sync_roles()
            await self.sync_users()
            
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

        new_message_stat_id = self.user_stat_type_id("new_message_count")

        # Sync code part
        async with self.sync():
            user = q.get_user_by_did(self.db, message.author.id)
            # Skip non-existing users
            if user is None:
                log.warn(f'{qualified_name(message.author)} does not exist in db! Skipping new message event!')
                return
            # Save event
            row = conv.new_message_to_row(user, message, self.event_type_map)
            log.debug(f'New message {row}')
            self.db.add(db.MessageEvent, row)
            # Update stats
            stat = q.get_user_stat_by_id(self.db, user.id, new_message_stat_id)
            if stat is None:
                empty_stat_row = conv.empty_user_stat_row(user.id, new_message_stat_id)
                stat = self.db.add(db.UserStat, empty_stat_row)
            stat.value += 1
            self.db.commit()
            # Update user rank
            await self.update_user_rank(user, message.author)


    async def on_control_message(self, message: discord.Message):
        """
            Async new control message event handler

            Calls appropriate control callback
        """
        prefix = self.config["control.prefix"]
        argv = parse_control_message(prefix, message)

        if argv is None or len(argv) == 0:
            return
            
        cmd_name = argv[0]

        if cmd_name == "help":
            help_lines = []
            line_fmt = res.get("messages.commands_list_entry")
            for cmd in self.commands:
                hook = self.commands[cmd]
                base_line = build_cmdcoro_usage(prefix, cmd, hook.or_cmdcoro)
                help_lines.append(line_fmt.format(base_line))
            help_header = res.get("messages.commands_list_head")
            help_msg = '\n'.join(help_lines)
            await message.channel.send(f'{help_header}\n{help_msg}\n')
            return

        if cmd_name not in self.commands:
            await message.channel.send(res.get("messages.unknown_command"))
            return
        
        await self.commands[cmd_name](self, message, prefix, argv)

    
    @after_initialized
    @event_config("message.edit")
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        """
            Async message edit event handler

            Saves event in database
        """
        if self.is_special_channel_id(payload.channel_id):
            return

        # ingore bot messages
        msg = q.get_msg_by_did(self.db, payload.message_id)
        if msg is None or msg.user.did in self.bot_members:
            return

        # Sync code part
        async with self.sync():
            row = conv.message_edit_row(msg, self.event_type_map)
            log.debug(f'Message edit {row}')
            self.db.add(db.MessageEvent, row)
            self.db.commit()
            # Update user rank
            member = await self.guild.fetch_member(msg.user.did)
            await self.update_user_rank(msg.user, member)

    
    @after_initialized
    @event_config("message.delete")
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """
            Async message delete event handler

            Saves event in database
        """
        if self.is_special_channel_id(payload.channel_id):
            return

        # ingore bot messages
        msg = q.get_msg_by_did(self.db, payload.message_id)
        if msg is None or msg.user.did in self.bot_members:
            return

        delete_message_stat_id = self.user_stat_type_id("delete_message_count")

        # Sync code part
        async with self.sync():
            row = conv.message_delete_row(msg, self.event_type_map)
            log.debug(f'Message delete {row}')
            self.db.add(db.MessageEvent, row)
            # Update stats
            stat = q.get_user_stat_by_id(self.db, msg.user_id, delete_message_stat_id)
            if stat is None:
                empty_stat_row = conv.empty_user_stat_row(msg.user_id, delete_message_stat_id)
                stat = self.db.add(db.UserStat, empty_stat_row)
            stat.value += 1
            self.db.commit()
            # Update user rank
            member = await self.guild.fetch_member(msg.user.did)
            await self.update_user_rank(msg.user, member)

    
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
            u_row = conv.member_row(member, self.role_map)
            user = self.db.update_or_add(db.User, 'did', u_row)
            log.debug(f'User join {u_row}')
            self.db.commit()
            # Add event
            e_row = conv.member_join_row(user, member.joined_at, self.event_type_map)
            self.db.add(db.MemberEvent, e_row)
            self.db.commit()

    
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
        # Sync code part
        async with self.sync():
            # Update user
            row = conv.member_row(after, self.role_map)
            user = self.db.update(db.User, 'did', row)
            if user is None:
                log.warn(f'{qualified_name(user)} does not exist in db! Skipping user update event!')
                return
            log.debug(f'User update {row}')
            self.db.commit()

    
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
            row = conv.user_row(member)
            if self.config["user.leave.keep"]:
                user = self.db.update(db.User, 'did', row)
                if user is None:
                    log.warn(f'{qualified_name(user)} does not exist in db! Skipping user leave event!')
                    return
                # Add event
                e_row = conv.user_leave_row(user, self.event_type_map)
                log.debug(f'User leave {e_row}')
                self.db.add(db.MemberEvent, e_row)
            else:
                log.debug(f'User leave (deleting) {row}')
                user = self.db.delete(db.User, 'did', row)
                if user is None:
                    log.warn(f'{qualified_name(user)} does not exist in db! Skipping user leave event!')
                    return
            self.db.commit()

    
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
            user = q.get_user_by_did(self.db, member.id)
            # Skip non-existing users
            if user is None:
                log.warn(f'{qualified_name(member)} does not exist in db! Skipping vc join event!')
                return
            # Apply constraints
            event = q.get_last_vc_event_by_id(self.db, user.id, channel.id)
            if event.type_id == self.event_type_id("vc_join"):
                # Skip absent vc leave
                log.warn(f'VC leave event is absent for {qualified_name(member)} in <{channel.name}! Removing last vc join event!')
                self.db.delete_model(event)
            # Save event
            row = conv.vc_join_row(user, channel, self.event_type_map)
            log.debug(f'VC join {row}')
            self.db.add(db.VoiceChatEvent, row)
            self.db.commit()
            
    
    @event_config("voice.leave")
    async def on_vc_leave(self, member: discord.Member, channel: discord.VoiceChannel):
        """
            Async vc join event handler

            Saves event in database
        """
        vc_time_stat_id = self.user_stat_type_id("vc_time")
        # Sync code part
        async with self.sync():
            user = q.get_user_by_did(self.db, member.id)
            # Skip non-existing users
            if user is None:
                log.warn(f'{qualified_name(member)} does not exist in db! Skipping vc leave event!')
                return
            # Apply constraints
            join_event = q.get_last_vc_event_by_id(self.db, user.id, channel.id)
            if join_event.type_id != self.event_type_id("vc_join"):
                # Skip absent vc join
                log.warn(f'VC join event is absent for {qualified_name(member)} in <{channel.name}! Skipping vc leave event!')
                return
            # Save event + update previous
            row = conv.vc_leave_row(user, channel, self.event_type_map)
            log.debug(f'VC join {row}')
            leave_event = self.db.add(db.VoiceChatEvent, row)
            self.db.touch(db.VoiceChatEvent, join_event.id)
            self.db.commit()
            # Update stats
            stat = q.get_user_stat_by_id(self.db, join_event.user_id, vc_time_stat_id)
            if stat is None:
                empty_stat_row = conv.empty_user_stat_row(user.id, vc_time_stat_id)
                stat = self.db.add(db.UserStat, empty_stat_row)
            stat.value += (leave_event.created_at - join_event.created_at).total_seconds()
            self.db.commit()
            # Update user rank
            await self.update_user_rank(user, member)

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
