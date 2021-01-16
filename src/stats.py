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
from bot import BotExtension
from util import qualified_name
from ovtype import *
import util.resources as res

log = logging.getLogger('stats-extension')

##################
# Stat Extension #
##################

class StatsExtension(BotExtension):
            
    #########
    # Hooks #
    #########
    
    async def on_message(self, msg: OverlordMessage) -> None:
        async with self.sync():
            user = self.bot.s_users.get(msg.discord.author)
            inc_value = self.bot.s_stats.get(user, 'new_message_count') + 1
            self.bot.s_stats.set(user, 'new_message_count', inc_value)

    async def on_message_edit(self, msg: OverlordMessage) -> None:
        async with self.sync():
            inc_value = self.bot.s_stats.get(msg.db.user, 'edit_message_count') + 1
            self.bot.s_stats.set(msg.db.user, 'edit_message_count', inc_value)

    async def on_message_delete(self, msg: OverlordMessage) -> None:
        async with self.sync():
            inc_value = self.bot.s_stats.get(msg.db.user, 'delete_message_count') + 1
            self.bot.s_stats.set(msg.db.user, 'delete_message_count', inc_value)

    async def on_vc_leave(self, user: OverlordUser, join: OverlordVCState, leave: OverlordVCState) -> None:
        async with self.sync():
            stat_val = self.bot.s_stats.get(user.db, 'vc_time')
            stat_val += (leave.db.created_at - join.db.created_at).total_seconds()
            self.bot.s_stats.set(user, 'vc_time', stat_val)
            
    #########
    # Tasks #
    #########

    @BotExtension.task(hours=12)
    async def stat_update_task(self):
        log.info("Scheduled stat update")
        async with self.sync():
            for stat_name in self.bot.s_stats.user_stat_type_map:
                self.bot.s_stats.reload_stat(stat_name)
        log.info("Done scheduled stat update")

    