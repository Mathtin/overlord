#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2020-present Daniel [Mathtin] Shiko <wdaniil@mail.ru>
Project: Overlord discord bot
Contributors: Danila [DeadBlasoul] Popov <dead.blasoul@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__author__ = "Mathtin"

import logging
import re

import discord

import db as DB
from overlord.extension import BotExtension
from util.resources import STRINGS as R
from util import is_dm_message

log = logging.getLogger('utility-extension')


#####################
# Utility Extension #
#####################

class UtilityExtension(BotExtension):

    __extname__ = '🛠 Utility Extension'
    __description__ = 'Basic utility commands collection'
    __color__ = 0xa83fc8

    PAGE_NUM_REGEX = re.compile(r'\[(\d+)/(\d+)]')

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
        else:  # if emoji == u'▶'
            page += 1
        ext = self.bot.resolve_extension(page)
        if ext is not None:
            i = self.bot.extension_idx(ext)
            e_count = len(self.bot.extensions)
            await msg.edit(embed=ext.help_embed(f"Overlord Help page [{i + 1}/{e_count}]"))
        if is_dm_message(msg):
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

    async def on_control_reaction_add(self, _, message: discord.Message,
                                      emoji: discord.PartialEmoji):
        if not message.embeds or message.author != self.bot.me or not emoji.is_unicode_emoji():
            return

        emoji = emoji.name
        embed = message.embeds[0]

        if 'Overlord Help page' in embed.author.name:
            await self.switch_help_page(emoji, message)

    async def on_control_reaction_remove(self, _, message: discord.Message,
                                         emoji: discord.PartialEmoji):
        if not message.embeds or message.author != self.bot.me or not emoji.is_unicode_emoji():
            return

        emoji = emoji.name
        embed = message.embeds[0]

        if 'Overlord Help page' in embed.author.name:
            await self.switch_help_page(emoji, message)

    ############
    # Commands #
    ############

    @BotExtension.command("help", description="Help pages")
    async def cmd_help(self, msg: discord.Message, opt_page_or_ext_name: str = '1'):
        ext = self.bot.resolve_extension(opt_page_or_ext_name)
        if ext is None:
            await msg.channel.send("No such help page")
            return
        i = self.bot.extension_idx(ext)
        e_count = len(self.bot.extensions)
        help_msg = await msg.channel.send(embed=ext.help_embed(f"Overlord Help page [{i + 1}/{e_count}]"))
        await help_msg.add_reaction(u'⏮')
        await help_msg.add_reaction(u'◀')
        await help_msg.add_reaction(u'▶')
        await help_msg.add_reaction(u'⏭')

    @BotExtension.command("ping", description="Checks bot state")
    async def cmd_ping(self, msg: discord.Message):
        if self.bot.sync().locked():
            await msg.channel.send(R.MESSAGE.STATUS.BUSY)
        else:
            await msg.channel.send(R.MESSAGE.STATUS.PING)

    @BotExtension.command("sync", description="Synchronize db data with guild data in terms of users and roles")
    async def cmd_sync_roles(self, msg: discord.Message):
        async with self.bot.sync():
            await msg.channel.send(R.MESSAGE.STATUS.SYNC_USERS)
            await self.bot.sync_users()
            await msg.channel.send(R.MESSAGE.STATUS.SUCCESS)

    @BotExtension.command("clear_all", description="Clears db data")
    async def clear_data(self, msg: discord.Message):
        models = [DB.MemberEvent, DB.MessageEvent, DB.VoiceChatEvent, DB.ReactionEvent, DB.UserStat, DB.User, DB.Role]
        async with self.bot.sync():
            log.warning("Clearing database")
            await self.bot.send_warning(self.__extname__, "Clearing database")
            for model in models:
                log.warning(f"Clearing table `{model.table_name()}`")
                await msg.channel.send(f'{R.MESSAGE.STATUS.DB_DROP_TABLE}: {model.table_name()}')
                self.bot.db.query(model).delete()
                self.bot.db.commit()
            await self.bot.sync_users()
            log.info(f'Done')
            await msg.channel.send(R.MESSAGE.STATUS.SUCCESS)

    @BotExtension.command("status", description="Prints bot state summary")
    async def extension_status(self, msg: discord.Message):
        report = f'{R.NAME.COMMON.GUILD}: {self.bot.guild.name}\n'
        report += f'{R.NAME.COMMON.MAINTAINER}: {self.bot.maintainer.mention}\n'
        report += f'{R.NAME.COMMON.CONTROL_CHANNEL}: {self.bot.control_channel.mention}\n'
        if self.bot.log_channel is not None:
            report += f'{R.NAME.COMMON.LOG_CHANNEL}: {self.bot.log_channel.mention}\n'
        embed = self.bot.new_info_report(R.EMBED.TITLE.SUMMARY, report)
        # Report extensions
        ext_details = [f'✅ {ext.name}' if ext.enabled else f'❌ {ext.name}' for ext in self.bot.extensions]
        embed.add_field(name=R.EMBED.TITLE.EXTENSION_STATUS_LIST, value='\n'.join(ext_details), inline=False)
        await msg.channel.send(embed=embed)

    @BotExtension.command("dump_channel", description="Fetches whole channel data into db (overwriting)")
    async def cmd_dump_channel(self, msg: discord.Message, channel: discord.TextChannel):
        permissions = channel.permissions_for(self.bot.me)
        if not permissions.read_message_history:
            await msg.channel.send(f'{channel.mention} {R.MESSAGE.ERROR.NO_ACCESS}: can\'t read message history')
            return

        # Transaction begins
        async with self.bot.sync():

            # Drop full channel message history
            log.warning(f'Dropping #{channel.name}({channel.id}) history')
            await msg.channel.send(f'{R.MESSAGE.STATUS.DB_CLEAR_CHANNEL}: {channel.mention}')
            self.bot.s_events.clear_text_channel_history(channel)

            # Load all messages
            log.warning(f'Loading #{channel.name}({channel.id}) history')
            await msg.channel.send(f'{R.MESSAGE.STATUS.DB_LOAD_CHANNEL}: {channel.mention}')
            async for message in channel.history(limit=None, oldest_first=True):

                # Skip bot messages
                if message.author.bot:
                    continue

                # Resolve user
                user = self.bot.s_users.get(message.author)
                if user is None and self.bot.config.keep_absent_users:
                    user = self.bot.s_users.add_user(message.author)

                # Skip users not in db
                if user is None:
                    continue

                # Insert new message event
                self.bot.s_events.create_new_message_event(user, message)

            log.info(f'Done')
            await msg.channel.send(R.MESSAGE.STATUS.SUCCESS)
