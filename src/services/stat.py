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

import db as DB
import db.converters as conv
import db.queries as q

from typing import Dict
from .event import EventService

log = logging.getLogger('stat-service')

##########################
# Service implementation #
##########################

class StatService(object):

    # State
    user_stat_type_map: Dict[str, int]

    # Members passed via constructor
    events: EventService
    db:     DB.DBSession

    def __init__(self, db: DB.DBSession, events: EventService) -> None:
        self.db = db
        self.events = events
        self.user_stat_type_map = {row.name:row.id for row in self.db.query(DB.UserStatType)}

    def check_stat_name(self, name: str) -> None:
        if name not in self.user_stat_type_map:
            raise NameError(f"No such stat name: {name}")

    def type_id(self, stat_name) -> int:
        return self.user_stat_type_map[stat_name]

    def get(self, user: DB.User, stat_name: str) -> int:
        self.check_stat_name(stat_name)
        stat = q.get_user_stat_by_id(self.db, user.id, self.type_id(stat_name))
        return stat.value if stat is not None else 0

    def set(self, user: DB.User, stat_name: str, value: int) -> None:
        type_id = self.type_id(stat_name)
        stat = q.get_user_stat_by_id(self.db, user.id, type_id)
        if stat is None:
            empty_stat_row = conv.empty_user_stat_row(user.id, type_id)
            stat = self.db.add(DB.UserStat, empty_stat_row)
        stat.value = value
        self.db.commit()

    def _reload_stat(self, query, stat: str, event: str) -> None:
        stat_id = self.user_stat_type_map[stat]
        event_id = self.events.type_id(event)
        self.db.query(DB.UserStat).filter_by(type_id=stat_id).delete()
        self.db.commit()
        select_query = query(event_id, [('type_id',stat_id)])
        insert_query = q.insert_user_stat_from_select(select_query)
        self.db.execute(insert_query)
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
        self._reload_stat(q.select_membership_time_per_user, 'membership', 'member_join')

    def reload_new_message_count_stat(self):
        self._reload_stat(q.select_message_count_per_user, 'new_message_count', 'new_message')

    def reload_delete_message_count_stat(self):
        self._reload_stat(q.select_message_count_per_user, 'delete_message_count', 'message_delete')

    def reload_edit_message_count_stat(self):
        self._reload_stat(q.select_message_count_per_user, 'edit_message_count', 'message_edit')

    def reload_new_reaction_count_stat(self):
        self._reload_stat(q.select_reaction_count_per_user, 'new_reaction_count', 'new_reaction')

    def reload_delete_reaction_count_stat(self):
        self._reload_stat(q.select_reaction_count_per_user, 'delete_reaction_count', 'reaction_delete')

    def reload_vc_time_stat(self):
        self._reload_stat(q.select_vc_time_per_user, 'vc_time', 'vc_join')

