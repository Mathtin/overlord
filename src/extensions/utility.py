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

import logging
import discord
import db as DB
from .base import BotExtension
import util.resources as res

log = logging.getLogger('utility-extension')

#####################
# Utility Extension #
#####################

class UtilityExtension(BotExtension):

    __extname__ = 'Utility Extension'
    __description__ = 'Basic utility commands collection'
    __color__ = 0xa83fc8
            
    #########
    # Tasks #
    #########

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
            
    @BotExtension.command("clear_all", desciption="Clears db data")
    async def clear_data(self, msg: discord.Message):
        models = [DB.MemberEvent, DB.MessageEvent, DB.VoiceChatEvent, DB.UserStat, DB.User, DB.Role]
        table_data_drop = res.get("messages.table_data_drop")
        async with self.bot.sync():
            log.warn("Clearing database")
            await self.bot.send_warning("Clearing database")
            for model in models:
                log.warn(f"Clearing table `{model.table_name()}`")
                await msg.channel.send(table_data_drop.format(model.table_name()))
                self.bot.db.query(model).delete()
                self.bot.db.commit()
            self.bot.set_awaiting_sync()
            log.info(f'Done')
            await msg.channel.send(res.get("messages.done"))

    @BotExtension.command("dump_channel", desciption="Fetches whole channel data into db (overwriting)")
    async def cmd_dump_channel(self, msg: discord.Message, channel_mention: str):
        channel = await self.bot.resolve_text_channel(channel_mention)
        vc_channel = await self.bot.resolve_voice_channel(channel_mention)
        if channel is None and vc_channel is not None:
            await msg.channel.send(res.get("messages.invalid_channel_type_text"))
            return
        elif channel is None:
            await msg.channel.send(res.get("messages.invalid_channel_mention"))
            return
        permissions = channel.permissions_for(self.bot.me)
        if not permissions.read_message_history:
            answer = res.get("messages.missing_access").format(channel.mention) + ' (can\'t read message history)'
            await msg.channel.send(answer)
            return

        # Tranaction begins
        async with self.bot.sync():

            # Drop full channel message history
            log.warn(f'Dropping #{channel.name}({channel.id}) history')
            answer = res.get("messages.channel_history_drop").format(channel.mention)
            await msg.channel.send(answer)
            self.bot.s_events.clear_text_channel_history(channel)

            # Load all messages
            log.warn(f'Loading #{channel.name}({channel.id}) history')
            answer = res.get("messages.channel_history_load").format(channel.mention)
            await msg.channel.send(answer)
            async for message in channel.history(limit=None,oldest_first=True):

                # Skip bot messages
                if message.author.bot:
                    continue

                # Resolve user
                user = self.bot.s_users.get(message.author)
                if user is None and self.bot.config["user.leave.keep"]:
                    user = self.bot.s_users.add_user(message.author)

                # Skip users not in db
                if user is None:
                    continue

                # Insert new message event
                self.bot.s_events.create_new_message_event(user, message)

            log.info(f'Done')
            await msg.channel.send(res.get("messages.done"))

