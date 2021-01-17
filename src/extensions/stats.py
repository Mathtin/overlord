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
from overlord import OverlordMessage, OverlordUser, OverlordVCState
from services import StatService
from util import pretty_days, pretty_seconds
import util.resources as res

log = logging.getLogger('stats-extension')

#################
# Utility funcs #
#################

def _build_stat_line(s_stats: StatService, user: DB.User, stat: str, formatter=lambda x:str(x)):
    stat_name = res.get(f"messages.{stat}_stat")
    stat_val = s_stats.get(user, stat)
    stat_val_f = formatter(stat_val)
    return res.get("messages.user_stats_entry").format(stat_name, stat_val_f)

##################
# Stat Extension #
##################

class StatsExtension(BotExtension):
            
    ###########
    # Methods #
    ###########

    @property
    def s_users(self):
        return self.bot.s_users

    @property
    def s_stats(self):
        return self.bot.s_stats
            
    #########
    # Hooks #
    #########
    
    async def on_message(self, msg: OverlordMessage) -> None:
        async with self.sync():
            user = self.s_users.get(msg.discord.author)
            inc_value = self.s_stats.get(user, 'new_message_count') + 1
            self.s_stats.set(user, 'new_message_count', inc_value)

    async def on_message_edit(self, msg: OverlordMessage) -> None:
        async with self.sync():
            inc_value = self.s_stats.get(msg.db.user, 'edit_message_count') + 1
            self.s_stats.set(msg.db.user, 'edit_message_count', inc_value)

    async def on_message_delete(self, msg: OverlordMessage) -> None:
        async with self.sync():
            inc_value = self.s_stats.get(msg.db.user, 'delete_message_count') + 1
            self.s_stats.set(msg.db.user, 'delete_message_count', inc_value)

    async def on_vc_leave(self, user: OverlordUser, join: OverlordVCState, leave: OverlordVCState) -> None:
        async with self.sync():
            stat_val = self.s_stats.get(user.db, 'vc_time')
            stat_val += (leave.db.created_at - join.db.created_at).total_seconds()
            self.s_stats.set(user, 'vc_time', stat_val)
            
    #########
    # Tasks #
    #########

    @BotExtension.task(hours=12)
    async def stat_update_task(self):
        log.info("Scheduled stat update")
        async with self.sync():
            for stat_name in self.s_stats.user_stat_type_map:
                self.s_stats.reload_stat(stat_name)
        log.info("Done scheduled stat update")
            
    ############
    # Commands #
    ############

    @BotExtension.command("recalculate_stats", desciption="Recalculate whole guild stats")
    async def cmd_recalculate_stats(self, msg: discord.Message):
        # Tranaction begins
        async with self.sync():
            log.info(f"Recalculating all stats")
            answer = res.get("messages.user_stat_calc")
            await msg.channel.send(answer.format('all'))
            for stat_type in self.s_stats.user_stat_type_map:
                self.s_stats.reload_stat(stat_type)
            log.info(f'Done')
            await msg.channel.send(res.get("messages.done"))

    @BotExtension.command("get_user_stats", desciption="Fetches user stats from db")
    async def cmd_get_user_stats(self, msg: discord.Message, user_mention: str):
        member = await self.bot.resolve_member_w_fb(user_mention, msg.channel)
        if member is None:
            return
        # Resolve user
        user = self.s_users.get(member)
        if user is None:
            await msg.channel.send(res.get("messages.unknown_user"))
            return

        answer = res.get("messages.user_stats_head").format(member.mention) + '\n'
        answer += _build_stat_line(self.s_stats, user, "membership", formatter=pretty_days) + '\n'
        answer += _build_stat_line(self.s_stats, user, "new_message_count") + '\n'
        answer += _build_stat_line(self.s_stats, user, "delete_message_count") + '\n'
        answer += _build_stat_line(self.s_stats, user, "edit_message_count") + '\n'
        answer += _build_stat_line(self.s_stats, user, "vc_time", formatter=pretty_seconds) + '\n'

        if self.s_stats.get(user, "min_weight") > 0:
            answer += _build_stat_line(self.s_stats, user, "min_weight") + '\n'
        if self.s_stats.get(user, "max_weight") > 0:
            answer += _build_stat_line(self.s_stats, user, "max_weight") + '\n'
        if self.s_stats.get(user, "exact_weight") > 0:
            answer += _build_stat_line(self.s_stats, user, "exact_weight") + '\n'

        await msg.channel.send(answer)
    
    @BotExtension.command("get_stat_names", desciption="Print stat names")
    async def cmd_get_stat_names(self, msg: discord.Message):
        names = [res.get("messages.stats_name_entry").format(s) for s in self.s_stats.user_stat_type_map]
        answer = res.get("messages.stats_name_head") + '\n' + '\n'.join(names)
        await msg.channel.send(answer)

    @BotExtension.command("get_user_stat", desciption="Fetches user stats from db (for specified user)")
    async def cmd_get_user_stat(self, msg: discord.Message, user_mention: str, stat_name: str):
        member = await self.bot.resolve_member_w_fb(user_mention, msg.channel)
        if member is None:
            return
        user = self.s_users.get(member)
        if user is None:
            await msg.channel.send(res.get("messages.unknown_user"))
            return
        try:
            answer = _build_stat_line(self.s_stats, user, stat_name)
            await msg.channel.send(answer)
        except NameError:
            await msg.channel.send(res.get("messages.error").format("Invalid stat name"))
            return

    @BotExtension.command("set_user_stat", desciption="Sets user stat value in db")
    async def cmd_set_user_stat(self, msg: discord.Message, user_mention: str, stat_name: str, value: str):
        member = await self.bot.resolve_member_w_fb(user_mention, msg.channel)
        if member is None:
            return
        try:
            value = int(value)
        except ValueError:
            await msg.channel.send(res.get("messages.error").format("integer expected"))
            return
        if value < 0:
            await msg.channel.send(res.get("messages.warning").format("negative stat value!"))
        user = self.s_users.get(member)
        if user is None:
            await msg.channel.send(res.get("messages.unknown_user"))
            return
        try:
            self.s_stats.set(user, stat_name, value)
            await msg.channel.send(res.get("messages.done"))
        except NameError:
            await msg.channel.send(res.get("messages.error").format("Invalid stat name"))
            return
