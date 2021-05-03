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

import db as DB
import db.converters as conv
import db.queries as q

from typing import Dict

from db.predefined import USER_STAT_TYPES
from .event import EventService
from .service import DBService

log = logging.getLogger('stat-service')


##########################
# Service implementation #
##########################

class StatService(DBService):
    # State
    user_stat_type_map: Dict[str, int]

    # Members passed via constructor
    events: EventService

    def __init__(self, db: DB.DBConnection, events: EventService) -> None:
        super().__init__(db)
        self.events = events
        with self.sync_session() as session:
            session.sync_table(model_type=DB.UserStatType, values=USER_STAT_TYPES, pk_col='name')
            session.commit()
            self.user_stat_type_map = {row.name: row.id for row in
                                       session.execute(q.select_stat_types()).scalars().all()}

    def check_stat_name(self, name: str) -> None:
        if name not in self.user_stat_type_map:
            raise NameError(f"No such stat name: {name}")

    def type_id(self, stat_name) -> int:
        return self.user_stat_type_map[stat_name]

    def get_sync(self, user: DB.User, stat_name: str) -> int:
        self.check_stat_name(stat_name)
        stat = self.get_optional_sync(q.select_user_stat_by_user_id(stat_name, user.id))
        return stat.value if stat is not None else 0

    async def get(self, user: DB.User, stat_name: str) -> int:
        self.check_stat_name(stat_name)
        stat = await self.get_optional(q.select_user_stat_by_user_id(stat_name, user.id))
        return stat.value if stat is not None else 0

    def set_sync(self, user: DB.User, stat_name: str, value: int) -> None:
        with self.sync_session() as session:
            with session.begin():
                stat = session.execute(q.select_user_stat_by_user_id(stat_name, user.id)).scalar_one_or_none()
                if stat is None:
                    empty_stat_row = conv.empty_user_stat_row(user.id, self.type_id(stat_name))
                    stat = session.add(model_type=DB.UserStat, value=empty_stat_row)
                stat.value = value

    async def set(self, user: DB.User, stat_name: str, value: int) -> None:
        async with self.session() as session:
            async with session.begin():
                stat = (await session.execute(q.select_user_stat_by_user_id(stat_name, user.id))).scalar_one_or_none()
                if stat is None:
                    empty_stat_row = conv.empty_user_stat_row(user.id, self.type_id(stat_name))
                    stat = session.add(model_type=DB.UserStat, value=empty_stat_row)
                stat.value = value

    def clear_all_sync(self):
        self.execute_sync(q.delete_all(DB.UserStat))

    async def clear_all(self):
        await self.execute(q.delete_all(DB.UserStat))

    def inc_sync(self, user: DB.User, stat_name: str) -> None:
        with self.sync_session() as session:
            with session.begin():
                stat = session.execute(q.select_user_stat_by_user_id(stat_name, user.id)).scalar_one_or_none()
                if stat is None:
                    empty_stat_row = conv.empty_user_stat_row(user.id, self.type_id(stat_name))
                    stat = session.add(model_type=DB.UserStat, value=empty_stat_row)
                stat.value += 1

    async def inc(self, user: DB.User, stat_name: str) -> None:
        async with self.session() as session:
            async with session.begin():
                stat = (await session.execute(q.select_user_stat_by_user_id(stat_name, user.id))).scalar_one_or_none()
                if stat is None:
                    empty_stat_row = conv.empty_user_stat_row(user.id, self.type_id(stat_name))
                    stat = session.add(model_type=DB.UserStat, value=empty_stat_row)
                stat.value += 1

    def dec_sync(self, user: DB.User, stat_name: str) -> None:
        with self.sync_session() as session:
            with session.begin():
                stat = session.execute(q.select_user_stat_by_user_id(stat_name, user.id)).scalar_one_or_none()
                if stat is None:
                    empty_stat_row = conv.empty_user_stat_row(user.id, self.type_id(stat_name))
                    stat = session.add(model_type=DB.UserStat, value=empty_stat_row)
                stat.value -= 1

    async def dec(self, user: DB.User, stat_name: str) -> None:
        async with self.session() as session:
            async with session.begin():
                stat = (await session.execute(q.select_user_stat_by_user_id(stat_name, user.id))).scalar_one_or_none()
                if stat is None:
                    empty_stat_row = conv.empty_user_stat_row(user.id, self.type_id(stat_name))
                    stat = session.add(model_type=DB.UserStat, value=empty_stat_row)
                stat.value -= 1

    def _reload_stat_sync(self, query, stat_name: str, event: str) -> None:
        stat_id = self.type_id(stat_name)
        with self.sync_session() as session:
            with session.begin():
                session.execute(q.delete_users_stat(stat_id))
                select_query = query(event, [('type_id', stat_id)])
                session.execute(q.insert_user_stat_from_select(select_query))

    async def _reload_stat(self, query, stat_name: str, event: str) -> None:
        stat_id = self.type_id(stat_name)
        async with self.session() as session:
            async with session.begin():
                await session.execute(q.delete_users_stat(stat_id))
                select_query = query(event, [('type_id', stat_id)])
                await session.execute(q.insert_user_stat_from_select(select_query))

    def reload_stat_sync(self, name: str) -> None:
        self.check_stat_name(name)
        if hasattr(self, f'reload_{name}_stat_sync'):
            hook = getattr(self, f'reload_{name}_stat_sync')
            hook()
        else:
            self.reload_stat_default_sync()

    def reload_stat_default_sync(self) -> None:
        pass

    async def reload_stat(self, name: str) -> None:
        self.check_stat_name(name)
        if hasattr(self, f'reload_{name}_stat'):
            hook = getattr(self, f'reload_{name}_stat')
            await hook()
        else:
            self.reload_stat_sync(name)

    def reload_membership_stat_sync(self) -> None:
        self._reload_stat_sync(q.select_membership_time_per_user, 'membership', 'member_join')

    async def reload_membership_stat(self) -> None:
        await self._reload_stat(q.select_membership_time_per_user, 'membership', 'member_join')

    def reload_new_message_count_stat_sync(self) -> None:
        self._reload_stat_sync(q.select_message_event_count_per_user, 'new_message_count', 'new_message')

    async def reload_new_message_count_stat(self) -> None:
        await self._reload_stat(q.select_message_event_count_per_user, 'new_message_count', 'new_message')

    def reload_delete_message_count_stat_sync(self) -> None:
        self._reload_stat_sync(q.select_message_event_count_per_user, 'delete_message_count', 'message_delete')

    async def reload_delete_message_count_stat(self) -> None:
        await self._reload_stat(q.select_message_event_count_per_user, 'delete_message_count', 'message_delete')

    def reload_edit_message_count_stat_sync(self) -> None:
        self._reload_stat_sync(q.select_message_event_count_per_user, 'edit_message_count', 'message_edit')

    async def reload_edit_message_count_stat(self) -> None:
        await self._reload_stat(q.select_message_event_count_per_user, 'edit_message_count', 'message_edit')

    def reload_new_reaction_count_stat_sync(self) -> None:
        self._reload_stat_sync(q.select_reaction_event_count_per_user, 'new_reaction_count', 'new_reaction')

    async def reload_new_reaction_count_stat(self) -> None:
        await self._reload_stat(q.select_reaction_event_count_per_user, 'new_reaction_count', 'new_reaction')

    def reload_delete_reaction_count_stat_sync(self) -> None:
        self._reload_stat_sync(q.select_reaction_event_count_per_user, 'delete_reaction_count', 'reaction_delete')

    async def reload_delete_reaction_count_stat(self) -> None:
        await self._reload_stat(q.select_reaction_event_count_per_user, 'delete_reaction_count', 'reaction_delete')

    def reload_vc_time_stat_sync(self) -> None:
        self._reload_stat_sync(q.select_vc_time_per_user, 'vc_time', 'vc_join')

    async def reload_vc_time_stat(self) -> None:
        await self._reload_stat(q.select_vc_time_per_user, 'vc_time', 'vc_join')
