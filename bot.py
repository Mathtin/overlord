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
import logging
import discord
import db

from util import *

log = logging.getLogger('overlord-bot')

class Overlord(discord.Client):

    def __init__(self, config: ConfigView, db_session: db.SQLiteSession):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        intents.messages = True

        super().__init__(intents=intents)

        self.token = os.getenv('DISCORD_TOKEN')
        self.guild_id = int(os.getenv('DISCORD_GUILD'))
        self.control_channel_id = int(os.getenv('DISCORD_CONTROL_CHANNEL'))
        self.error_channel_id = int(os.getenv('DISCORD_ERROR_CHANNEL'))

        self.config = config
        self.db = db_session

        # Values initiated on_ready
        self.guild = None
        self.control_channel = None
        self.error_channel = None

    def run(self):
        super().run(self.token)

    #########
    # Hooks #
    #########

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

    async def on_ready(self):
        # Lock current async context
        init_lock = asyncio.Lock()
        async with init_lock:
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

            # Sync roles
            roles = []
            for i in range(len(self.guild.roles)):
                r = role_to_row(self.guild.roles[i])
                r['position'] = i
                roles.append(r)
            self.db.sync_table(db.Role, 'did', roles)
            self.db.commit()
            
            # Message for pterodactyl panel
            print(self.config["egg_done"])

    async def on_message(self, message: discord.Message):
        # ingore own messages
        if message.author == self.user:
            return

        # ingore any foreign messages
        if is_dm_message(message) or message.guild.id != self.guild.id:
            return

        user = self.db.query(db.User).filter(db.User.did == message.author.id).first()

        if user is None:
            log.error(f'{qualified_name(message.author)} does not exist in db! Skipping new message event!')
            return

        event = db.Event()

    async def on_raw_message_edit1(self, payload: discord.RawMessageUpdateEvent):
        sinks = self.get_attached_sinks(payload.channel_id)
        if sinks is None:
            return

        channel = self.get_channel(payload.channel_id)

        msg = await channel.fetch_message(payload.message_id)

        # ingore own messages
        if msg.author.id == self.user.id:
            return

        for sink in sinks:
            if "on_message_edit" not in sink:
                continue
            await sink["on_message_edit"](self, msg)

    async def on_raw_message_delete1(self, payload: discord.RawMessageUpdateEvent):
        sinks = self.get_attached_sinks(payload.channel_id)
        if sinks is None:
            return

        for sink in sinks:
            if "on_message_delete" not in sink:
                continue
            await sink["on_message_delete"](self, payload.message_id)

    async def on_member_remove1(self, member: discord.Member):

        # ingore any foreign members
        if member.guild.id != self.guild.id:
            return
        
        if 'remove' in self.member_hooks:
            await self.member_hooks["remove"](self, member)

    async def on_control_message1(self, message: discord.Message):
        argv = parse_control_message(message)

        if argv is None or len(argv) == 0:
            return
            
        cmd_name = argv[0]

        if cmd_name == "help":
            help_lines = []
            for cmd in self.commands:
                hook = self.commands[cmd]
                help_lines.append(build_cmdcoro_usage(cmd, hook.or_cmdcoro))
            help_msg = '\n'.join(help_lines)
            await message.channel.send(f'Available commands:\n`######------######\n{help_msg}\n######------######`')
            return

        if cmd_name not in self.commands:
            await message.channel.send("Unknown command")
            return
        
        await self.commands[cmd_name](self, message, argv)
