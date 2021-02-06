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

import re
import logging
import discord
import db as DB
import util
from .base import BotExtension
import util.resources as res

log = logging.getLogger('utility-extension')

#####################
# Utility Extension #
#####################

class UtilityExtension(BotExtension):

    __extname__ = '🛠 Utility Extension'
    __description__ = 'Basic utility commands collection'
    __color__ = 0xa83fc8

    PAGE_NUM_REGEX = re.compile(r'\[(\d+)/(\d+)\]')
            
    ###########
    # Methods #
    ###########

    async def switch_help_page(self, emoji, msg: discord.Message):
        embed = msg.embeds[0]
        page = int(re.search(UtilityExtension.PAGE_NUM_REGEX, embed.author.name).group(1))
        if emoji == u'⏮':
            page = 1
        elif emoji == u'⏭':
            page = len(self.bot.extensions)
        elif emoji == u'◀':
            page -= 1
        else: # if emoji == u'▶'
            page += 1
        ext = self.bot.resolve_extension(page)
        if ext is not None:
            i = self.bot.extension_idx(ext)
            l = len(self.bot.extensions)
            await msg.edit(embed=ext.help_embed(f"Overlord Help page [{i+1}/{l}]"))
        if util.is_dm_message(msg):
            return
        for reaction in msg.reactions:
            users = await reaction.users().flatten()
            for user in users:
                if user == self.bot.me:
                    continue
                await reaction.remove(user)

    #########
    # Hooks #
    #########

    async def on_control_reaction_add(self, member: discord.Member, message: discord.Message, emoji: discord.PartialEmoji):
        if not message.embeds or message.author != self.bot.me or not emoji.is_unicode_emoji():
            return

        emoji = emoji.name
        embed = message.embeds[0]
        
        if 'Overlord Help page' in embed.author.name:
            await self.switch_help_page(emoji, message)
            
    ############
    # Commands #
    ############

    @BotExtension.command("help", desciption="Help pages")
    async def cmd_help(self, msg: discord.Message, optional_page: str='1'):
        ext = self.bot.resolve_extension(optional_page)
        if ext is None:
            await msg.channel.send("No such help page")
            return
        i = self.bot.extension_idx(ext)
        l = len(self.bot.extensions)
        help_msg = await msg.channel.send(embed=ext.help_embed(f"Overlord Help page [{i+1}/{l}]"))
        await help_msg.add_reaction(u'⏮')
        await help_msg.add_reaction(u'◀')
        await help_msg.add_reaction(u'▶')
        await help_msg.add_reaction(u'⏭')
        return


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
            self.bot.sync_users()
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

