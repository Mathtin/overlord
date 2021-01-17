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

import json
import logging

import discord
import db as DB
from services.role import RoleService
from services.stat import StatService
import util.resources as res

from typing import Optional, List, Tuple, Dict
from .base import BotExtension
from util import qualified_name, dict_fancy_table, quote_msg
from util import ConfigView
from util.exceptions import InvalidConfigException
from util.extbot import filter_roles, is_role_applied
from overlord import OverlordMessage, OverlordUser, OverlordVCState

log = logging.getLogger('ranking-extension')

#####################
# Ranking Extension #
#####################
class RankingExtension(BotExtension):
            
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
    def ranks(self) -> Dict[str, Dict[str, int]]:
        return self.bot.config["ranks.role"]

    @property
    def required_roles(self) -> List[str]:
        return self.bot.config["ranks.require"]

    @property
    def ignored_roles(self) -> List[str]:
        return self.bot.config["ranks.ignore"]
            
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
            exact_ranks = [(n,r) for n,r in ranks if r['weight'] == exact_weight]
            return exact_ranks[0] if exact_ranks else None

        # Filter minimal
        if min_weight > 0:
            ranks = [(n,r) for n,r in ranks if r['weight'] >= min_weight]

        # Filter maximal
        if max_weight > 0:
            ranks = [(n,r) for n,r in ranks if r['weight'] <= max_weight]

        # Filter meeting criteria
        meet_criteria = lambda n,r: (messages >= r["messages"] or vc_time >= r["vc"]) and membership >= r["membership"]
        ranks = [(n,r) for n,r in ranks if meet_criteria(n,r)]

        return max(ranks, key=lambda nr: nr[1]["weight"])[0] if ranks else None

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
        if self.bot.awaiting_sync():
            log.warn("Cannot update user rank: awaiting role sync")
            return
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
        if self.bot.awaiting_sync():
            log.error("Cannot update user ranks: awaiting role sync")
            return
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
        # Check ranks config
        for role_name in self.ignored_roles:
            if self.s_roles.get(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", "bot.ranks.ignore")
        for role_name in self.required_roles:
            if self.s_roles.get(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", "bot.ranks.require")
        ranks_weights = {}
        for rank_name in self.ranks:
            rank = ConfigView(value=self.ranks[rank_name], schema_name="rank_schema")
            if self.s_roles.get(rank_name) is None:
                raise InvalidConfigException(f"No such role: '{rank_name}'", "bot.ranks.role")
            if rank['weight'] in ranks_weights:
                dup_rank = ranks_weights[rank['weight']]
                raise InvalidConfigException(f"Duplicate weights '{rank_name}', '{dup_rank}'", "bot.ranks.role")
            ranks_weights[rank['weight']] = rank_name

    async def on_message(self, msg: OverlordMessage) -> None:
        async with self.sync():
            await self.update_rank(msg.discord.author)

    async def on_message_edit(self, msg: OverlordMessage) -> None:
        async with self.sync():
            if self.bot.s_users.is_absent(msg.db.user):
                return
            member = await self.bot.guild.fetch_member(msg.db.user.did)
            await self.update_rank(member)

    async def on_message_delete(self, msg: OverlordMessage) -> None:
        async with self.sync():
            if self.bot.s_users.is_absent(msg.db.user):
                return
            member = await self.bot.guild.fetch_member(msg.db.user.did)
            await self.update_rank(member)
            
    async def on_vc_leave(self, user: OverlordUser, join: OverlordVCState, leave: OverlordVCState) -> None:
        async with self.sync():
            await self.update_rank(user.discord.member)
            
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
    async def cmd_update_rank(self, msg: discord.Message, user_mention: str):
        member = await self.bot.resolve_member_w_fb(user_mention, msg.channel)
        if member is None:
            return
        async with self.sync():
            await msg.channel.send(res.get("messages.update_rank_begin").format(member.mention))
            await self.update_rank(member)
            await msg.channel.send(res.get("messages.done"))
        
    @BotExtension.command("list_ranks", desciption="List all configured ranks")
    async def cmd_list_ranks(self, msg: discord.Message):
        ranks = self.bot.config["ranks.role"]
        table_header = res.get('messages.rank_table_header')
        table = dict_fancy_table(ranks, key_name='rank')
        await msg.channel.send(f'{table_header}\n{quote_msg(table)}')

    @BotExtension.command("add_rank", desciption="Creates new user rank")
    async def cmd_add_rank(self, msg: discord.Message, role_name: str, weight: str, membership: str, msg_count: str, vc_time: str):
        try:
            weight = int(weight)
            membership = int(membership)
            messages_count = int(msg_count)
            vc_time = int(vc_time)
        except ValueError:
            await msg.channel.send(res.get("messages.rank_arg_parse_error"))
            return
        role = self.bot.get_role(role_name)
        if role is None:
            await msg.channel.send(res.get("messages.rank_role_unknown").format(role_name))
            return
        ranks = self.bot.config.ranks.role.copy().value()
        if role_name in ranks:
            await msg.channel.send(res.get("messages.rank_role_exists"))
            return
        ranks_weights = {ranks[r]['weight']:r for r in ranks}
        if weight in ranks_weights:
            await msg.channel.send(res.get("messages.rank_role_same_weight").format(ranks_weights[weight]))
            return
        ranks[role_name] = {
            "weight": weight,
            "membership": membership,
            "messages": messages_count,
            "vc": vc_time
        }
        path = 'bot.ranks.role'

        try:
            err = await self.bot.safe_alter_config(path, ranks)
        except KeyError:
            log.info(f'Invalid config path provided: {path}')
            await msg.channel.send(res.get("messages.invalid_config_path"))
            return False
        
        if not err:
            self.bot.save_config()
            log.info(f'Done')
            await msg.channel.send(res.get("messages.done"))
        else:
            answer = res.get("messages.error").format(err) + '\n' + res.get("messages.warning").format('Config reverted')
            await msg.channel.send(answer)


    @BotExtension.command("remove_rank", desciption="Update specified user rank")
    async def cmd_remove_rank(self, msg: discord.Message, role_name: str):
        role = self.bot.get_role(role_name)
        if role is None:
            await msg.channel.send(res.get("messages.rank_role_unknown").format(role_name))
            return
        ranks = self.bot.config.ranks.role.copy().value()
        if role_name not in ranks:
            await msg.channel.send(res.get("messages.rank_unknown"))
            return
        del ranks[role_name]
        path = 'bot.ranks.role'

        try:
            err = await self.bot.safe_alter_config(path, ranks)
        except KeyError:
            log.info(f'Invalid config path provided: {path}')
            await msg.channel.send(res.get("messages.invalid_config_path"))
            return False
        
        if not err:
            self.bot.save_config()
            log.info(f'Done')
            await msg.channel.send(res.get("messages.done"))
        else:
            answer = res.get("messages.error").format(err) + '\n' + res.get("messages.warning").format('Config reverted')
            await msg.channel.send(answer)

    @BotExtension.command("edit_rank", desciption="Update specified user rank")
    async def cmd_edit_rank(self, msg: discord.Message, role_name: str, weight: str, membership: str, msg_count: str, vc_time: str):
        try:
            weight = int(weight)
            membership = int(membership)
            messages_count = int(msg_count)
            vc_time = int(vc_time)
        except ValueError:
            await msg.channel.send(res.get("messages.rank_arg_parse_error"))
            return
        role = self.bot.get_role(role_name)
        if role is None:
            await msg.channel.send(res.get("messages.rank_role_unknown").format(role_name))
            return
        ranks = self.bot.config.ranks.role.copy().value()
        if role_name not in ranks:
            await msg.channel.send(res.get("messages.rank_unknown"))
            return
        ranks_weights = {ranks[r]['weight']:r for r in ranks}
        if weight in ranks_weights and ranks_weights[weight] != role_name:
            await msg.channel.send(res.get("messages.rank_role_same_weight").format(ranks_weights[weight]))
            return
        ranks[role_name] = {
            "weight": weight,
            "membership": membership,
            "messages": messages_count,
            "vc": vc_time
        }
        path = 'bot.ranks.role'

        try:
            err = await self.bot.safe_alter_config(path, ranks)
        except KeyError:
            log.info(f'Invalid config path provided: {path}')
            await msg.channel.send(res.get("messages.invalid_config_path"))
            return False
        
        if not err:
            self.bot.save_config()
            log.info(f'Done')
            await msg.channel.send(res.get("messages.done"))
        else:
            answer = res.get("messages.error").format(err) + '\n' + res.get("messages.warning").format('Config reverted')
            await msg.channel.send(answer)
