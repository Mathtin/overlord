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
from typing import Dict, List, Optional

import discord

from overlord.types import OverlordMember
from util import InvalidConfigException
from .base import BotExtension

log = logging.getLogger('config-extension')

####################
# Invite Extension #
####################

class InviteExtension(BotExtension):

    __extname__ = '🚪 Invite Extension'
    __description__ = 'User invite handling'
    __color__ = 0x7623bc

    # State
    __invites = List[discord.Invite]
            
    ###########
    # Methods #
    ###########

    @property
    def invites(self) -> Dict[str, Dict[str, str]]:
        return self.bot.config["invites"]

    def find_invite(self, code) -> Optional[discord.Invite]:
        for inv in self.__invites:
            if inv.code == code:
                return inv
        return None
            
    #################
    # Async Methods #
    #################

    async def handle_invite(self, member: discord.Member, invite: discord.Invite):
        invites = self.invites
        if not invite.code in invites:
            return
        role_name = invites[invite.code]["role"]
        role = self.bot.s_roles.get(role_name)
        await member.add_roles(role)

    #########
    # Hooks #
    #########

    async def on_ready(self) -> None:
        self.__invites = await self.bot.guild.invites()

    async def on_config_update(self) -> None:
        for code, conf in self.invites.items():
            if self.find_invite(code) is None:
                raise InvalidConfigException(f"No such invite code: '{code}'", "bot.invites")
            role = conf["role"]
            if self.bot.s_roles.get(conf["role"]) is None:
                raise InvalidConfigException(f"No such role: '{role}'", "bot.invites")
            
    
    async def on_member_join(self, member: OverlordMember) -> None:

        invites_after = await member.discord.guild.invites()

        for new_invite in invites_after:
        
            old_invite = self.find_invite(new_invite.code)
            if old_invite is None or old_invite.uses == new_invite.uses:
                continue

            await self.handle_invite(member.discord, new_invite)

        self.__invites = invites_after

    async def on_member_remove(self, member: OverlordMember):
        self.__invites = await member.discord.guild.invites()

            
    ############
    # Commands #
    ############

    


