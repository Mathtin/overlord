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

from db.session import DBSession
import os
import sys
import traceback
import logging
import discord
import db
import db.queries as q

from util import *

log = logging.getLogger('overlord-bot')

class Overlord(discord.Client):

    # Members loaded from ENV
    token: str
    guild_id: int
    control_channel_id: int
    error_channel_id: int

    # Members passed via constructor
    config: ConfigView
    db: DBSession

    # Event name -> id (gathered via db)
    event_type_map: dict

    # Values initiated on_ready
    guild: discord.Guild
    control_channel: discord.TextChannel
    error_channel: discord.TextChannel
    role_map: dict
    commands: dict
    bot_members: dict
    initialized: bool

    def __init__(self, config: ConfigView, db_session: db.DBSession):
        self.config = config
        self.db = db_session

        # Init base class
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        intents.messages = True

        super().__init__(intents=intents)

        # Load env values
        self.token = os.getenv('DISCORD_TOKEN')
        self.guild_id = int(os.getenv('DISCORD_GUILD'))
        self.control_channel_id = int(os.getenv('DISCORD_CONTROL_CHANNEL'))
        self.error_channel_id = int(os.getenv('DISCORD_ERROR_CHANNEL'))

        # Map event types
        self.event_type_map = {row.name:row.id for row in self.db.query(db.EventType)}

        # Preset some values initiated on_ready
        self.commands = {}
        self.bot_members = {}
        self.initialized = False

    def run(self):
        super().run(self.token)

    def event_type(self, name):
        return self.event_type_map[name]

    #########
    # Hooks #
    #########

    """
        Async error event handler

        Sends stackktrace to error channel
    """
    async def on_error(self, event, *args, **kwargs):
        ex_type = sys.exc_info()[0]

        logging.exception(f'Error on event: {event}')

        exception_lines = traceback.format_exception(*sys.exc_info())

        exception_msg = '`' + ''.join(exception_lines).replace('`', '\'') + '`'

        if self.error_channel is not None:
            await self.error_channel.send(exception_msg)

        if ex_type is InvalidConfigException:
            await self.logout()
        if ex_type is NotCoroutineException:
            await self.logout()


    """
        Async ready event handler

        Completly initialize bot state
    """
    async def on_ready(self):
        # Lock current async context
        async with asyncio.Lock():
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

            # Sync and map roles
            log.info(f'Syncing roles')
            roles = roles_to_rows(self.guild.roles)
            self.role_map = { role['did']: role for role in roles }
            self.db.sync_table(db.Role, 'did', roles)
            log.info(f'Commiting changes')
            self.db.commit()

            # Sync users
            log.info(f'Syncing users')
            async for member in self.guild.fetch_members(limit=None):
                # Skip bots
                if member.bot:
                    self.bot_members[member.id] = member
                    continue
                row = member_to_row(member, self.role_map)
                self.db.update_or_add(db.User, 'did', row)
                self.db.commit()
            log.info(f'Syncing done')
            
            # Message for pterodactyl panel
            print(self.config["egg_done"])
            self.initialized = True

    """
        Async new message event handler

        Saves event in database
    """
    async def on_message(self, message: discord.Message):
        if not self.initialized or not self.config["event.message.new.track"]:
            return

        # ingore own messages
        if message.author == self.user:
            return

        # ingore any foreign messages
        if is_dm_message(message) or message.guild.id != self.guild.id:
            return

        # ignore bot messages
        if message.author.id in self.bot_members:
            return

        if message.channel == self.control_channel:
            await self.on_control_message(message)
            return

        user = q.get_user_by_id(self.db, message.author.id)

        if user is None:
            log.warn(f'{qualified_name(message.author)} does not exist in db! Skipping new message event!')
            return

        event_id = self.event_type("new_message")
        row = new_message_to_row(message, event_id)
        log.info(f'New message {row}')
        self.db.add(db.MessageEvent(**row))
        self.db.commit()


    """
        Async new control message event handler

        Calls appropriate control callback
    """
    async def on_control_message(self, message: discord.Message):
        prefix = self.config["control.prefix"]
        argv = parse_control_message(prefix, message)

        if argv is None or len(argv) == 0:
            return
            
        cmd_name = argv[0]

        if cmd_name == "help":
            help_lines = []
            for cmd in self.commands:
                hook = self.commands[cmd]
                help_lines.append(build_cmdcoro_usage(prefix, cmd, hook.or_cmdcoro))
            help_msg = '\n'.join(help_lines)
            await message.channel.send(f'`Available commands:\n{help_msg}\n`')
            return

        if cmd_name not in self.commands:
            await message.channel.send("Unknown command")
            return
        
        await self.commands[cmd_name](self, message, argv)


    """
        Async message edit event handler

        Saves event in database
    """
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if not self.initialized or not self.config["event.message.edit.track"]:
            return

        # ignore special channel events
        if payload.channel_id == self.control_channel.id or \
            payload.channel_id == self.error_channel.id:
            return

        # ingore bot messages
        msg = q.get_msg_by_id(self.db, payload.message_id)
        if msg is None or msg.author_id in self.bot_members:
            return

        event_id = self.event_type("message_edit")
        row = message_change_row(msg, event_id)
        log.info(f'Message edit: {row}')
        self.db.add(db.MessageEvent(**row))
        self.db.commit()


    """
        Async message delete event handler

        Saves event in database
    """
    async def on_raw_message_delete(self, payload: discord.RawMessageUpdateEvent):
        if not self.initialized or not self.config["event.message.delete.track"]:
            return

        # ignore special channel events
        if payload.channel_id == self.control_channel.id or \
            payload.channel_id == self.error_channel.id:
            return

        # ingore bot messages
        msg = q.get_msg_by_id(self.db, payload.message_id)
        if msg is None or msg.author_id in self.bot_members:
            return

        event_id = self.event_type("message_delete")
        row = message_change_row(msg, event_id)
        log.info(f'Message delete: {row}')
        self.db.add(db.MessageEvent(**row))
        self.db.commit()


    """
        Async member join event handler

        Saves user in database
    """
    async def on_member_join(self, member: discord.Member):
        if not self.initialized or not self.config["event.user.join.track"]:
            return

        # Skip bots
        if member.bot:
            self.bot_members[member.id] = member
            return

        # ingore any foreign members
        if member.guild.id != self.guild.id:
            return

        row = member_to_row(member, self.role_map)
        self.db.update_or_add(db.User, 'did', row)
        self.db.commit()


    """
        Async member remove event handler

        Removes user from database (or keep it, depends on config)
    """
    async def on_member_remove(self, member: discord.Member):
        if not self.initialized or not self.config["event.user.left.track"]:
            return

        # Skip bots
        if member.bot:
            return

        # ingore any foreign members
        if member.guild.id != self.guild.id:
            return
        
        # Resolve user
        user = q.get_user_by_id(self.db, member.id)
        if user is None:
            return

        # Apply actions
        if self.config["user.left.keep"]:
            row = user_to_row(member)
            self.db.update(db.User, 'did', row)
        else:
            self.db.delete(user)
        
        # Commit changes
        self.db.commit()
