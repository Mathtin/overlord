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

import asyncio
import logging

import discord
from discord.ext import tasks
import db as DB
import db.queries as q
import db.converters as conv

from util import *
from typing import Dict, List, Optional

############
# Services #
############

class RoleService(object):

    log = logging.getLogger('role-service')
    
    role_map: Dict[str, discord.Role]
    role_rows_did_map: Dict[int, DB.Role]

    # Members passed via constructor
    db:         DB.DBSession

    def __init__(self, db: DB.DBSession):
        self.db = db

    def load(self, roles: List[discord.Role]):
        self.role_map = { role.name: role for role in roles }
        roles = conv.roles_to_rows(roles)
        self.role_rows_did_map = { role['did']: role for role in roles }
        # Sync table
        self.db.sync_table(DB.Role, 'did', roles)

    def get(self, role_name: str) -> discord.Role:
        if role_name in self.role_map:
            return self.role_map[role_name]
        return None

class UserService(object):

    log = logging.getLogger('user-service')

    # Members passed via constructor
    db:             DB.DBSession
    roles:          RoleService
    bot_cache:      Dict[int, discord.User]

    def __init__(self, db: DB.DBSession, roles: RoleService):
        self.db = db
        self.roles = roles
        self.bot_cache = {}
        
    def mark_everyone_absent(self):
        self.db.query(DB.User).update({'roles': None, 'display_name': None})
        self.db.commit()

    def cache_bot(self, duser: discord.User):
        if duser.bot:
            self.bot_cache[duser.id] = duser
            
    def update_member(self, member: discord.Member) -> DB.User:
        u_row = conv.member_row(member, self.roles.role_rows_did_map)
        user = self.db.update_or_add(DB.User, 'did', u_row)
        self.db.commit()
        return user
            
    def add_user(self, user: discord.User) -> DB.User:
        u_row = conv.user_row(user)
        user = self.db.add(DB.User, u_row)
        self.db.commit()
        return user

    def remove_absent(self):
        self.db.query(DB.User).filter_by(roles=None).delete()
        self.db.commit()

    def remove(self, member: discord.Member) -> bool:
        user = self.get(member)
        if user is None:
            return None
        user.delete()
        self.db.commit()
        return user
        
    def mark_absent(self, member: discord.Member) -> bool:
        user = self.get(member)
        if user is None:
            return None
        user.roles = None
        user.display_name = None
        self.db.commit()
        return user

    def get(self, member: discord.User) -> DB.User:
        return q.get_user_by_did(self.db, member.id)

    def get_by_display_name(self, display_name: str) -> DB.User:
        return self.db.query(DB.User).filter_by(display_name=display_name).first()

    def get_by_qualified_name(self, qualified_name: str) -> DB.User:
        if '#' not in qualified_name:
            raise ValueError(f"Invalid qualified name: {qualified_name}")
        [name, disc] = qualified_name.split('#')
        disc = int(disc)
        return self.db.query(DB.User).filter_by(name=name, disc=disc).first()


class EventService(object):

    log = logging.getLogger('event-service')

    # Members passed via constructor
    db:         DB.DBSession

    # Maps
    event_type_map: Dict[str, int]

    def __init__(self, db: DB.DBSession):
        self.db = db
        self.event_type_map = {row.name:row.id for row in self.db.query(DB.EventType)}

    def check_event_name(self, name: str):
        if name not in self.event_type_map:
            raise NameError(f"No such event name: {name}")

    def get_last_vc_event(self, user: DB.User, channel: discord.VoiceChannel) -> int:
        return q.get_last_vc_event_by_id(self.db, user.id, channel.id)

    def get_last_member_event(self, member: discord.Member) -> int:
        return q.get_last_member_event_by_did(self.db, member.id)

    def get_last_user_member_event(self, user: DB.User) -> int:
        return q.get_last_member_event_by_id(self.db, user.id)

    def get_message(self, did: int):
        return q.get_msg_by_did(self.db, did)

    def type_id(self, event_name: str) -> int:
        return self.event_type_map[event_name]

    def repair_member_joined_event(self, member: discord.Member, user: DB.User):
        last_event = self.get_last_user_member_event(user)
        if last_event is None or last_event.type_id != self.type_id("member_join"):
            e_row = conv.member_join_row(user, member.joined_at, self.event_type_map)
            last_event = self.db.add(DB.MemberEvent, e_row)
        last_event.created_at = member.joined_at
        self.db.commit()

    def repair_vc_leave_event(self, user: DB.User, channel: discord.VoiceChannel):
        last_event = self.get_last_vc_event(user, channel)
        if last_event is not None and last_event.type_id == self.type_id("vc_join"):
            EventService.log.warn(f'VC leave event is absent for last vc_join event for {user} in <{channel.name}! Removing last vc_join event!')
            self.db.delete_model(last_event)
            self.db.commit()

    def create_member_join_event(self, user: DB.User, member: discord.Member):
        e_row = conv.member_join_row(user, member.joined_at, self.event_type_map)
        self.db.add(DB.MemberEvent, e_row)
        self.db.commit()

    def create_user_leave_event(self, user: DB.User):
        e_row = conv.user_leave_row(user, self.event_type_map)
        self.db.add(DB.MemberEvent, e_row)
        self.db.commit()

    def create_new_message_event(self, user: DB.User, message: discord.Message):
        row = conv.new_message_to_row(user.id, message, self.event_type_map)
        self.db.add(DB.MessageEvent, row)
        self.db.commit()

    def create_message_edit_event(self, msg: DB.MessageEvent):
        row = conv.message_edit_row(msg, self.event_type_map)
        self.db.add(DB.MessageEvent, row)
        self.db.commit()

    def create_message_delete_event(self, msg: DB.MessageEvent):
        row = conv.message_delete_row(msg, self.event_type_map)
        self.db.add(DB.MessageEvent, row)
        self.db.commit()

    def create_vc_join_event(self, user: DB.User, channel: discord.VoiceChannel):
        e_row = conv.vc_join_row(user, channel, self.event_type_map)
        self.db.add(DB.VoiceChatEvent, e_row)
        self.db.commit()

    def create_vc_leave_event(self, user: DB.User, channel: discord.VoiceChannel):
        e_row = conv.vc_leave_row(user, channel, self.event_type_map)
        self.db.add(DB.VoiceChatEvent, e_row)
        self.db.commit()

    def close_vc_join_event(self, user: DB.User, channel: discord.VoiceChannel) -> DB.VoiceChatEvent:
        last_event = self.get_last_vc_event(user, channel)
        if last_event is None or last_event.type_id != self.type_id("vc_join"):
            # Skip absent vc join
            EventService.log.warn(f'VC join event is absent for {user} in <{channel.name}! Skipping vc leave event!')
            return None
        # Save event + update previous
        e_row = conv.vc_leave_row(user, channel, self.event_type_map)
        self.db.add(DB.VoiceChatEvent, e_row)
        self.db.touch(DB.VoiceChatEvent, last_event.id)
        self.db.commit()
        return last_event

    def clear_text_channel_history(self, channel: discord.TextChannel):
        self.db.query(DB.MessageEvent).filter_by(channel_id=channel.id).delete()
        self.db.commit()



class StatService(object):

    log = logging.getLogger('stat-service')

    # Members passed via constructor
    events:     EventService
    db:         DB.DBSession

    # Maps
    user_stat_type_map: Dict[str, int]

    def __init__(self, db: DB.DBSession, events: EventService):
        self.db = db
        self.events = events
        self.user_stat_type_map = {row.name:row.id for row in self.db.query(DB.UserStatType)}

    def get_stat_update_task(self, mtx: asyncio.Lock, **kwargs) -> asyncio.AbstractEventLoop:
        @tasks.loop(**kwargs)
        async def stat_update_task():
            StatService.log.info("Scheduled stat update")
            async with mtx:
                for stat_name in self.user_stat_type_map:
                    self.reload_stat(stat_name)
            StatService.log.info("Done scheduled stat update")
        return stat_update_task

    def check_stat_name(self, name: str):
        if name not in self.user_stat_type_map:
            raise NameError(f"No such stat name: {name}")

    def __reload_stat(self, query, stat: str, event: str):
        stat_id = self.user_stat_type_map[stat]
        event_id = self.events.type_id(event)
        self.db.query(DB.UserStat).filter_by(type_id=stat_id).delete()
        self.db.commit()
        select_query = query(event_id, [('type_id',stat_id)])
        insert_query = q.insert_user_stat_from_select(select_query)
        self.db.execute(insert_query)
        self.db.commit()

    def type_id(self, stat_name):
        return self.user_stat_type_map[stat_name]

    def get(self, user: DB.User, stat_name: str) -> int:
        self.check_stat_name(stat_name)
        stat = q.get_user_stat_by_id(self.db, user.id, self.type_id(stat_name))
        return stat.value if stat is not None else 0

    def set(self, user: DB.User, stat_name: str, value: int):
        type_id = self.type_id(stat_name)
        stat = q.get_user_stat_by_id(self.db, user.id, type_id)
        if stat is None:
            empty_stat_row = conv.empty_user_stat_row(user.id, type_id)
            stat = self.db.add(DB.UserStat, empty_stat_row)
        stat.value = value
        self.db.commit()

    def reload_stat(self, name: str):
        self.check_stat_name(name)
        if hasattr(self, f'reload_{name}_stat'):
            hook = getattr(self, f'reload_{name}_stat')
            hook()
        else:
            self.reload_stat_default()

    def reload_stat_default(self):
        pass

    def reload_membership_stat(self):
        self.__reload_stat(q.select_membership_time_per_user, 'membership', 'member_join')

    def reload_new_message_count_stat(self):
        self.__reload_stat(q.select_message_count_per_user, 'new_message_count', 'new_message')

    def reload_delete_message_count_stat(self):
        self.__reload_stat(q.select_message_count_per_user, 'delete_message_count', 'message_delete')

    def reload_edit_message_count_stat(self):
        self.__reload_stat(q.select_message_count_per_user, 'edit_message_count', 'message_edit')

    def reload_vc_time_stat(self):
        self.__reload_stat(q.select_vc_time_per_user, 'vc_time', 'vc_join')


class RankingService(object):

    log = logging.getLogger('ranking-service')

    # Members passed via constructor
    stats:      StatService
    roles:      RoleService
    db:         DB.DBSession
    config:     ConfigView
    mtx:        asyncio.Lock

    def __init__(self, stats: StatService, roles: RoleService, config: ConfigView):
        self.stats = stats
        self.roles = roles
        self.config = config

    ###########
    # Methods #
    ###########

    def check_config(self):
        # Check ranks config
        ignore_roles = self.config["ignore"]
        for role_name in ignore_roles:
            if self.roles.get(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", "bot.ranks.ignore")
        require_roles = self.config["require"]
        for role_name in require_roles:
            if self.roles.get(role_name) is None:
                raise InvalidConfigException(f"No such role: '{role_name}'", "bot.ranks.require")
        ranks = self.config["role"]
        ranks_weights = {}
        for rank_name in ranks:
            rank = ConfigView(value=ranks[rank_name], schema_name="rank_schema")
            if self.roles.get(rank_name) is None:
                raise InvalidConfigException(f"No such role: '{rank_name}'", "bot.ranks.role")
            if rank['weight'] in ranks_weights:
                dup_rank = ranks_weights[rank['weight']]
                raise InvalidConfigException(f"Duplicate weights '{rank_name}', '{dup_rank}'", "bot.ranks.role")
            ranks_weights[rank['weight']] = rank_name

    def find_user_rank_name(self, user: DB.User) -> Optional[str]:
        # Gather stat values
        exact_weight = self.stats.get(user, "exact_weight")
        min_weight = self.stats.get(user, "min_weight")
        max_weight = self.stats.get(user, "max_weight")
        membership = self.stats.get(user, "membership")
        messages = self.stats.get(user, "new_message_count") - self.stats.get(user, "delete_message_count")
        vc_time = self.stats.get(user, "vc_time")
        
        # Prepare rank search
        ranks = self.config["role"]
        max_rank_weight = -1000
        max_rank_name = None

        # Search ranks
        for rank_name in ranks:
            rank = ConfigView(value=ranks[rank_name], schema_name="rank_schema")
            # Handle exact
            if exact_weight > 0:
                if rank["weight"] == exact_weight:
                    return rank_name
                else:
                    continue
            # Handle minimal
            if min_weight > 0:
                if rank["weight"] == min_weight and max_rank_weight < rank["weight"]:
                    max_rank_weight = rank["weight"]
                    max_rank_name = rank_name
                elif rank["weight"] < min_weight:
                    continue
            # Handle maximal
            if max_weight > 0:
                if rank["weight"] > max_weight:
                    continue
            # Predicate value
            meet_requirements = (messages >= rank["messages"] or vc_time >= rank["vc"]) and membership >= rank["membership"]
            # Result expression
            if meet_requirements and max_rank_weight < rank["weight"]:
                max_rank_weight = rank["weight"]
                max_rank_name = rank_name
        
        return max_rank_name

    def ignore_member(self, member: discord.Member) -> bool:
        return len(filter_roles(member, self.config["ignore"])) > 0 or len(filter_roles(member, self.config["require"])) == 0

    def roles_to_add_and_remove(self, member: discord.Member, user: DB.User) -> List[discord.Role]:
        rank_roles = [self.roles.get(r) for r in self.config['role']]
        applied_rank_roles = filter_roles(member, rank_roles)
        effective_rank_name = self.find_user_rank_name(user)
        ranks_to_remove = [r for r in applied_rank_roles if r.name != effective_rank_name]
        ranks_to_apply = []
        if effective_rank_name is not None and not is_role_applied(member, effective_rank_name):
            ranks_to_apply.append(self.roles.get(effective_rank_name))
        return ranks_to_apply, ranks_to_remove

