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
from util import InvalidConfigException, ConfigView
from .base import BotExtension

log = logging.getLogger('config-extension')

#################
# Invite Config #
#################

class InviteRootConfig(ConfigView):
    """
    invite {
        role {
            ... = "..."
        }
    }
    """
    role : Dict[str, str] = {}

####################
# Invite Extension #
####################

class InviteExtension(BotExtension):

    __extname__ = '🚪 Invite Extension'
    __description__ = 'User invite handling'
    __color__ = 0x7623bc

    # State
    _invites = List[discord.Invite]
    _invite_role_map: Dict[str, List[str]]
    config: InviteRootConfig
            
    ###########
    # Methods #
    ###########

    def find_invite(self, code) -> Optional[discord.Invite]:
        for inv in self._invites:
            if inv.code == code:
                return inv
        return None
            
    #################
    # Async Methods #
    #################

    async def handle_invite(self, member: discord.Member, invite: discord.Invite):
        if not invite.code in self._invite_role_map:
            return
        role_names = self._invite_role_map[invite.code]
        roles = [self.bot.s_roles.get(r) for r in role_names]
        await member.add_roles(*roles)

    #########
    # Hooks #
    #########

    async def on_ready(self) -> None:
        self._invites = await self.bot.guild.invites()

    async def on_config_update(self) -> None:
        self._invite_role_map = {}
        self.config = self.bot.get_config_section(InviteRootConfig)
        if self.config is None:
            raise InvalidConfigException("InviteRootConfig section not found", "root")
        for role, code in self.config.role.items():
            if self.bot.s_roles.get(role) is None:
                raise InvalidConfigException(f"No such role: '{role}'", self.config.path('role'))
            if self.find_invite(code) is None:
                raise InvalidConfigException(f"No such invite code: '{code}'", self.config.path(f'role.{role}'))
            if code not in self._invite_role_map:
                self._invite_role_map[code] = []
            self._invite_role_map[code].append(role)
            
    async def on_member_join(self, member: OverlordMember) -> None:
        invites_after = await self.bot.guild.invites()
        for new_invite in invites_after:
            old_invite = self.find_invite(new_invite.code)
            if old_invite is None or old_invite.uses == new_invite.uses:
                continue
            await self.handle_invite(member.discord, new_invite)
        self._invites = invites_after

    async def on_member_remove(self, member: OverlordMember):
        self._invites = await self.bot.guild.invites()
            
    ############
    # Commands #
    ############

    


