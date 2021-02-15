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

import logging

import discord

import db as DB
from overlord import OverlordMessage, OverlordVCState, OverlordMember
from services import StatService
from util import FORMATTERS
from util.extbot import qualified_name
from util.resources import R
from .base import BotExtension

log = logging.getLogger('stats-extension')


#################
# Utility funcs #
#################

def _build_stat_line(s_stats: StatService, user: DB.User, stat: str) -> str:
    stat_name = R.get(f"name.user_stat.{stat}")
    stat_val = s_stats.get(user, stat)
    stat_val_f = FORMATTERS[stat](stat_val) if stat in FORMATTERS else str(stat_val)
    return f'{stat_name}: {stat_val_f}'


def _add_stat_field(embed: discord.Embed, s_stats: StatService, user: DB.User, stat: str) -> None:
    stat_name = R.get(f"name.user_stat.{stat}")
    stat_val = s_stats.get(user, stat)
    stat_val_f = FORMATTERS[stat](stat_val) if stat in FORMATTERS else str(stat_val)
    embed.add_field(name=stat_name, value=stat_val_f, inline=False)


##################
# Stat Extension #
##################

class StatsExtension(BotExtension):
    __extname__ = '📊 Stats Extension'
    __description__ = 'Gathers member stats (messages, vc, membership and etc.)'
    __color__ = 0x3fbbc8

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
            user = msg.db.user
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

    async def on_vc_leave(self, user: OverlordMember, join: OverlordVCState, leave: OverlordVCState) -> None:
        async with self.sync():
            stat_val = self.s_stats.get(user.db, 'vc_time')
            stat_val += (leave.db.created_at - join.db.created_at).total_seconds()
            self.s_stats.set(user.db, 'vc_time', stat_val)

    async def on_reaction_add(self, member: OverlordMember, _, __) -> None:
        async with self.sync():
            inc_value = self.s_stats.get(member.db, 'new_reaction_count') + 1
            self.s_stats.set(member.db, 'new_reaction_count', inc_value)

    async def on_reaction_remove(self, member: OverlordMember, _, __) -> None:
        async with self.sync():
            inc_value = self.s_stats.get(member.db, 'delete_reaction_count') + 1
            self.s_stats.set(member.db, 'delete_reaction_count', inc_value)

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

    @BotExtension.command("recalculate_stats", description="Recalculate whole guild stats")
    async def cmd_recalculate_stats(self, msg: discord.Message):
        # Transaction begins
        async with self.sync():
            log.info(f"Recalculating all stats")
            await msg.channel.send(R.MESSAGE.STATUS.CALC_STATS)
            for stat_type in self.s_stats.user_stat_type_map:
                self.s_stats.reload_stat(stat_type)
            log.info(f'Done')
            await msg.channel.send(R.MESSAGE.SUCCESS)

    @BotExtension.command("get_user_stats", description="Fetches user stats from db")
    async def cmd_get_user_stats(self, msg: discord.Message, ov_user: OverlordMember):
        member = ov_user.discord
        user = ov_user.db

        desc = f'{member.mention} stats gathered so far by me'
        embed = self.bot.new_embed(f"📊 {qualified_name(member)} stats", desc, header="Overlord Stats",
                                   color=self.__color__)

        _add_stat_field(embed, self.s_stats, user, "membership")
        _add_stat_field(embed, self.s_stats, user, "new_message_count")
        _add_stat_field(embed, self.s_stats, user, "delete_message_count")
        _add_stat_field(embed, self.s_stats, user, "edit_message_count")
        _add_stat_field(embed, self.s_stats, user, "new_reaction_count")
        _add_stat_field(embed, self.s_stats, user, "delete_reaction_count")
        _add_stat_field(embed, self.s_stats, user, "vc_time")

        if self.s_stats.get(user, "min_weight") > 0:
            _add_stat_field(embed, self.s_stats, user, "min_weight")
        if self.s_stats.get(user, "max_weight") > 0:
            _add_stat_field(embed, self.s_stats, user, "max_weight")
        if self.s_stats.get(user, "exact_weight") > 0:
            _add_stat_field(embed, self.s_stats, user, "exact_weight")

        await msg.channel.send(embed=embed)

    @BotExtension.command("get_stat_names", description="Print stat names")
    async def cmd_get_stat_names(self, msg: discord.Message):
        desc = f'Stat code names available at the moment'
        embed = self.bot.new_embed(f"Stat names", desc, header="Overlord Stats", color=self.__color__)
        for stat in self.s_stats.user_stat_type_map:
            stat_name = R.get(f"name.user_stat.{stat}")
            embed.add_field(name=stat_name, value=f'`{stat}`', inline=False)
        await msg.channel.send(embed=embed)

    @BotExtension.command("get_user_stat", description="Fetches user stats from db (for specified user)")
    async def cmd_get_user_stat(self, msg: discord.Message, user: DB.User, stat_name: str):
        try:
            answer = _build_stat_line(self.s_stats, user, stat_name)
            await msg.channel.send(answer)
        except NameError:
            embed = self.bot.new_error_report(R.MESSAGE.ERROR_OTHER.UNKNOWN_STAT, '')
            await msg.channel.send(embed=embed)
            return

    @BotExtension.command("set_user_stat", description="Sets user stat value in db")
    async def cmd_set_user_stat(self, msg: discord.Message, user: DB.User, stat_name: str, value: int):
        if value < 0:
            embed = self.bot.new_error_report(R.MESSAGE.ERROR_OTHER.NEGATIVE_STAT_VALUE, '')
            await msg.channel.send(embed=embed)
        try:
            self.s_stats.set(user, stat_name, value)
            await msg.channel.send(R.MESSAGE.SUCCESS)
        except NameError:
            embed = self.bot.new_error_report(R.MESSAGE.ERROR_OTHER.UNKNOWN_STAT, '')
            await msg.channel.send(embed=embed)
            return
