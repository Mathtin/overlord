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
import util.resources as res

from typing import Callable, Optional, List, Tuple, Dict

from util import ConfigView, FORMATTERS
from util.exceptions import InvalidConfigException
from util.extbot import filter_roles, is_role_applied, qualified_name
from services.role import RoleService
from services.stat import StatService
from overlord.types import OverlordMember, OverlordMessageDelete, OverlordMessageEdit, OverlordMessage, OverlordVCState

from .base import BotExtension

log = logging.getLogger('ranking-extension')

##################
# Ranking Config #
##################

class RankConfig(ConfigView):
    """
    ... {
        weight = ...
        membership = ...
        messages = ...
        vc = ...
    }
    """
    weight     : int = 0
    membership : int = 1
    messages   : int = 1
    vc         : int = 1


class RankingRootConfig(ConfigView):
    """
    rank {
        ignored = [...]
        required = [...]
        role {
            ... : RankConfig
        }
    }
    """
    ignored  : List[str]             = []
    required : List[str]             = []
    role     : Dict[str, RankConfig] = {}


#####################
# Ranking Extension #
#####################
class RankingExtension(BotExtension):

    __extname__ = 'Ranking Extension'
    __description__ = 'Member ranking system based on stats (check Stats Extension)'
    __color__ = 0xc84e3f

    config: RankingRootConfig
            
    #########
    # Props #
    #########

    @property
    def s_stats(self) -> StatService:
        return self.bot.s_stats

    @property
    def s_roles(self) -> RoleService:
        return self.bot.s_roles

    @property
    def ranks(self) -> Dict[str, RankConfig]:
        return self.config.role

    @property
    def required_roles(self) -> List[str]:
        return self.config.required

    @property
    def ignored_roles(self) -> List[str]:
        return self.config.ignored
            
    ###########
    # Methods #
    ###########

    def find_user_rank_name(self, user: DB.User) -> Optional[str]:

        # Gather stat values
        exact_weight = self.s_stats.get(user, "exact_weight")
        min_weight = self.s_stats.get(user, "min_weight")
        max_weight = self.s_stats.get(user, "max_weight")
        membership = self.s_stats.get(user, "membership")
        messages = self.s_stats.get(user, "new_message_count") - self.s_stats.get(user, "delete_message_count")
        vc_time = self.s_stats.get(user, "vc_time")
        ranks = self.ranks.items()

        # Search exact
        if exact_weight > 0:
            exact_ranks = [(n,r) for n,r in ranks if r.weight == exact_weight]
            return exact_ranks[0] if exact_ranks else None

        # Filter minimal
        if min_weight > 0:
            ranks = [(n,r) for n,r in ranks if r.weight >= min_weight]

        # Filter maximal
        if max_weight > 0:
            ranks = [(n,r) for n,r in ranks if r.weight <= max_weight]

        # Filter meeting criteria
        meet_criteria : Callable[[str,RankConfig], bool] = \
            lambda n,r: (messages >= r.messages or vc_time >= r.vc) and membership >= r.membership

        ranks = [(n,r) for n,r in ranks if meet_criteria(n,r)]

        return max(ranks, key=lambda nr: nr[1].weight)[0] if ranks else None

    def ignore_member(self, member: discord.Member) -> bool:
        return len(filter_roles(member, self.ignored_roles)) > 0 or len(filter_roles(member, self.required_roles)) == 0

    def roles_to_add_and_remove(self, member: discord.Member, user: DB.User) -> Tuple[List[discord.Role], List[discord.Role]]:
        rank_roles = [self.s_roles.get(r) for r in self.ranks]
        applied_rank_roles = filter_roles(member, rank_roles)
        effective_rank_name = self.find_user_rank_name(user)
        ranks_to_remove = [r for r in applied_rank_roles if r.name != effective_rank_name]
        ranks_to_apply = []
        if effective_rank_name is not None and not is_role_applied(member, effective_rank_name):
            ranks_to_apply.append(self.s_roles.get(effective_rank_name))
        return ranks_to_apply, ranks_to_remove
            
    #################
    # Async Methods #
    #################

    async def update_rank(self, member: discord.Member):
        # Resolve user
        if member.bot:
            return
        user = self.bot.s_users.get(member)
        # Skip non-existing users
        if user is None:
            log.warn(f'{qualified_name(member)} does not exist in db! Skipping user rank update!')
            return
        # Ignore inappropriate members
        if self.ignore_member(member):
            return
        # Resolve roles to move
        roles_add, roles_del = self.roles_to_add_and_remove(member, user)
        # Remove old roles
        if roles_del:
            log.info(f"Removing {qualified_name(member)}'s rank roles: {roles_del}")
            await member.remove_roles(*roles_del)
        # Add new roles
        if roles_add:
            log.info(f"Adding {qualified_name(member)}'s rank roles: {roles_add}")
            await member.add_roles(*roles_add)
        # Update user in db
        self.bot.s_users.update_member(member)

    async def update_all_ranks(self) -> None:
        log.info(f'Updating user ranks')
        async for member in self.bot.guild.fetch_members(limit=None):
            if member.bot:
                continue
            await self.update_rank(member)
        log.info(f'Done updating user ranks')
            
    #########
    # Hooks #
    #########

    async def on_config_update(self) -> None:
        self.config = self.bot.get_config_section(RankingRootConfig)
        if self.config is None:
            raise InvalidConfigException("RankingRootConfig section not found", "root")
        # Check rank roles
        for i,role_name in enumerate(self.ignored_roles):
            if self.s_roles.get(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", self.config.path(f"ignored[{i}]"))
        for i,role_name in enumerate(self.required_roles):
            if self.s_roles.get(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", self.config.path(f"required[{i}]"))
        # Check rank weights
        ranks_weights = {}
        for name, props in self.ranks.items():
            if self.s_roles.get(name) is None:
                raise InvalidConfigException(f"No such role: '{name}'", self.config.path("role"))
            if props.weight in ranks_weights:
                dup_rank = ranks_weights[props.weight]
                raise InvalidConfigException(f"Duplicate weights '{name}', '{dup_rank}'", self.config.path(f"role.{name}"))
            ranks_weights[props.weight] = name

    async def on_message(self, msg: OverlordMessage) -> None:
        async with self.sync():
            await self.update_rank(msg.discord.author)

    async def on_message_edit(self, msg: OverlordMessageEdit) -> None:
        async with self.sync():
            if self.bot.s_users.is_absent(msg.db.user):
                return
            member = await self.bot.guild.fetch_member(msg.db.user.did)
            await self.update_rank(member)

    async def on_message_delete(self, msg: OverlordMessageDelete) -> None:
        async with self.sync():
            if self.bot.s_users.is_absent(msg.db.user):
                return
            member = await self.bot.guild.fetch_member(msg.db.user.did)
            await self.update_rank(member)
            
    async def on_vc_leave(self, user: OverlordMember, join: OverlordVCState, leave: OverlordVCState) -> None:
        async with self.sync():
            await self.update_rank(user.discord)
            
    ############
    # Commands #
    ############

    @BotExtension.command("update_all_ranks", desciption="Fetches all members of guild and updates each rank")
    async def cmd_update_all_ranks(self, msg: discord.Message):
        async with self.sync():
            await msg.channel.send(res.get("messages.update_ranks_begin"))
            await self.update_all_ranks()
            await msg.channel.send(res.get("messages.done"))

    @BotExtension.command("update_rank", desciption="Update specified user rank")
    async def cmd_update_rank(self, msg: discord.Message, member: discord.Member):
        async with self.sync():
            await msg.channel.send(res.get("messages.update_rank_begin").format(member.mention))
            await self.update_rank(member)
            await msg.channel.send(res.get("messages.done"))
        
    @BotExtension.command("list_ranks", desciption="List all configured ranks")
    async def cmd_list_ranks(self, msg: discord.Message):
        desc = f'Configured ranks list'
        embed = self.bot.base_embed("Overlord Ranking", f"🎖 Ranks", desc, self.__color__)
        for name, rank in self.ranks.items():
            lines = [f'{p}: {FORMATTERS[p](v)}' for p,v in rank.items()]
            rank_s = '\n'.join(lines)
            embed.add_field(name=name, value=rank_s, inline=True)
        await msg.channel.send(embed=embed)

    @BotExtension.command("add_rank", desciption="Creates new user rank")
    async def cmd_add_rank(self, msg: discord.Message, role: discord.Role, weight: int, membership: int, msg_count: int, vc_time: int):
        # Check already existed rank for specified role 
        if role.name in self.ranks:
            await msg.channel.send(res.get("messages.rank_role_exists"))
            return
        # Check weight uniqueness
        ranks_weights = {r.weight for r in self.ranks.values()}
        if weight in ranks_weights:
            await msg.channel.send(res.get("messages.rank_role_same_weight").format(ranks_weights[weight]))
            return
        # Add new rank
        rank = RankConfig()
        rank.weight = weight
        rank.membership = membership
        rank.messages = msg_count
        rank.vc = vc_time
        self.ranks[role.name] = rank
        # Update config properly
        err = await self.bot.safe_update_config()
        if not err:
            answer = res.get("messages.done")
        else:
            answer = res.get("messages.error").format(err) + '\n' + res.get("messages.warning").format('Config reverted')
        await msg.channel.send(answer)

    @BotExtension.command("remove_rank", desciption="Update specified user rank")
    async def cmd_remove_rank(self, msg: discord.Message, role: discord.Role):
        if role.name not in self.ranks:
            await msg.channel.send(res.get("messages.rank_unknown"))
            return
        del self.ranks[role.name]
        # Update config properly
        err = await self.bot.safe_update_config()
        if not err:
            answer = res.get("messages.done")
        else:
            answer = res.get("messages.error").format(err) + '\n' + res.get("messages.warning").format('Config reverted')
        await msg.channel.send(answer)

    @BotExtension.command("edit_rank", desciption="Update specified user rank")
    async def cmd_edit_rank(self, msg: discord.Message, role: discord.Role, weight: int, membership: int, msg_count: int, vc_time: int):
        if role.name not in self.ranks:
            await msg.channel.send(res.get("messages.rank_unknown"))
            return
        # Check weight uniqueness
        ranks_weights = {r.weight for r in self.ranks.values()}
        if weight in ranks_weights:
            await msg.channel.send(res.get("messages.rank_role_same_weight").format(ranks_weights[weight]))
            return
        # Update rank
        rank = self.ranks[role.name]
        rank.weight = weight
        rank.membership = membership
        rank.messages = msg_count
        rank.vc = vc_time
        # Update config properly
        err = await self.bot.safe_update_config()
        if not err:
            answer = res.get("messages.done")
        else:
            answer = res.get("messages.error").format(err) + '\n' + res.get("messages.warning").format('Config reverted')
        await msg.channel.send(answer)
