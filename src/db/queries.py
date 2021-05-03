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

from datetime import datetime
from typing import Any, Tuple, List, Type

from sqlalchemy import func, and_, literal_column, Column
from sqlalchemy.sql import Select, Insert, Update, Delete
from sqlalchemy.sql.expression import cast, delete, text, extract
from sqlalchemy.sql.expression import insert, select, update
from sqlalchemy.sql.sqltypes import Integer

from .models import *
from .models.base import BaseModel


def date_to_secs_sqlite(col: Column):
    return cast(func.strftime('%s', col), Integer)


def date_to_secs_mysql(col: Column):
    return func.unix_timestamp(col)


def date_to_secs_postgresql(col: Column):
    return extract('epoch', col)


MODE_SQLITE = 'sqlite'
MODE_MYSQL = 'mysql'
MODE_POSTGRESQL = 'postgresql'
MODE = MODE_MYSQL


def date_to_secs(col: Column):
    if MODE == MODE_SQLITE:
        return date_to_secs_sqlite(col)
    if MODE == MODE_MYSQL:
        return date_to_secs_mysql(col)
    if MODE == MODE_POSTGRESQL:
        return date_to_secs_postgresql(col)


##################
# SELECT QUERIES #
##################

def select_role(role_name: str) -> Select:
    return select(Role).where(Role.name == role_name)


def select_event_type(event_type: str) -> Select:
    return select(EventType).where(EventType.name == event_type)


def select_event_types() -> Select:
    return select(EventType)


def select_stat_types() -> Select:
    return select(UserStatType)


def select_user_by_did(did: int) -> Select:
    return select(User).where(User.did == did)


def select_user_by_display_name(display_name: str) -> Select:
    return select(User).where(User.display_name == display_name)


def select_user_by_q_name(name: str, disc: int) -> Select:
    return select(User).where(User.name == name, User.disc == disc)


def select_message_event_by_did(type_id: int, did: int) -> Select:
    return select(MessageEvent).where(and_(MessageEvent.message_id == did, MessageEvent.type_id == type_id))


def select_last_member_event_by_user_did(user_did: int) -> Select:
    return select(MemberEvent) \
        .join(User) \
        .where(User.did == user_did) \
        .order_by(MemberEvent.created_at.desc()) \
        .limit(1)


def select_last_member_event_by_user_id(user_id: int) -> Select:
    return select(MemberEvent) \
        .where(MemberEvent.user_id == user_id) \
        .order_by(MemberEvent.created_at.desc()) \
        .limit(1)


def select_any_last_vc_event_by_user_id(user_id: int, channel_id: int) -> Select:
    return select(VoiceChatEvent) \
        .where(and_(VoiceChatEvent.user_id == user_id, VoiceChatEvent.channel_id == channel_id)) \
        .order_by(VoiceChatEvent.created_at.desc()) \
        .limit(1)


def select_last_vc_event_by_user_id(channel_id: int, event_name: str, user_id: int) -> Select:
    return select(VoiceChatEvent) \
        .join(EventType) \
        .where(and_(VoiceChatEvent.user_id == user_id,
                    VoiceChatEvent.channel_id == channel_id,
                    EventType.name == event_name)) \
        .order_by(VoiceChatEvent.created_at.desc())


def select_user_stat_by_user_id(stat_name: str, user_id: int) -> Select:
    return select(UserStat) \
        .join(UserStatType) \
        .where(and_(UserStat.user_id == user_id,
                    UserStatType.name == stat_name))


def select_membership_time_per_user(event_name: str, lit_values: List[Tuple[str, Any]] = None) -> Select:
    if lit_values is None:
        lit_values = []
    join_time = date_to_secs(func.max(MemberEvent.created_at))
    current_time = int(datetime.now().timestamp())
    membership_value = cast((current_time - join_time) / 86400, Integer).label('value')
    return select([membership_value, MemberEvent.user_id] +
                  [literal_column(str(v)).label(label) for label, v in lit_values]) \
        .join(User) \
        .join(EventType) \
        .where(and_(EventType.name == event_name,
                    User.roles.isnot(None))) \
        .group_by(MemberEvent.user_id)


def select_message_event_count_per_user(event_name: str, lit_values: List[Tuple[str, Any]] = None) -> Select:
    if lit_values is None:
        lit_values = []
    value_column = func.count(MessageEvent.id).label('value')
    return select([value_column, MessageEvent.user_id] +
                  [literal_column(str(v)).label(label) for label, v in lit_values]) \
        .join(EventType) \
        .where(EventType.name == event_name) \
        .group_by(MessageEvent.user_id)


def select_reaction_event_count_per_user(event_name: str, lit_values: List[Tuple[str, Any]] = None) -> Select:
    if lit_values is None:
        lit_values = []
    value_column = func.count(ReactionEvent.id).label('value')
    return select([value_column, ReactionEvent.user_id] +
                  [literal_column(str(v)).label(label) for label, v in lit_values]) \
        .join(EventType) \
        .where(EventType.name == event_name) \
        .group_by(ReactionEvent.user_id)


def select_vc_time_per_user(event_name: str, lit_values: List[Tuple[str, Any]] = None) -> Select:
    if lit_values is None:
        lit_values = []
    join_time = date_to_secs(VoiceChatEvent.created_at)
    left_time = date_to_secs(VoiceChatEvent.updated_at)
    value_column = func.sum(left_time - join_time).label('value')
    return select([value_column, VoiceChatEvent.user_id] +
                  [literal_column(str(v)).label(label) for label, v in lit_values]) \
        .join(EventType) \
        .where(EventType.name == event_name) \
        .group_by(VoiceChatEvent.user_id)


##################
# INSERT QUERIES #
##################

def insert_user_stat_from_select(select_query: Select, values: list = None) -> Insert:
    if values is None:
        values = ['value', 'user_id', 'type_id']
    return insert(UserStat).inline().from_select(values, select_query)


##################
# UPDATE QUERIES #
##################

def update_all_users_absent() -> Update:
    return update(User) \
        .values(roles=None, display_name=None)


def update_user_absent(id_: int) -> Update:
    return update(User) \
        .values(roles=None, display_name=None) \
        .where(User.id == id_)


def update_user_absent_by_did(did: int) -> Update:
    return update(User) \
        .values(roles=None, display_name=None) \
        .where(User.did == did)


def update_inc_user_member_stat(user_id: int, type_id: int) -> Update:
    return update(UserStat) \
        .values(value=UserStat.value + 1) \
        .where(and_(UserStat.user_id == user_id,
                    UserStat.type_id == type_id))


def update_dec_user_member_stat(user_id: int, type_id: int) -> Update:
    return update(UserStat) \
        .values(value=UserStat.value - 1) \
        .where(and_(UserStat.user_id == user_id,
                    UserStat.type_id == type_id))


##################
# DELETE QUERIES #
##################

def delete_absent_users() -> Delete:
    return delete(User) \
        .where(User.roles.is_(None), User.display_name.is_(None))


def delete_message_events_by_channel_id(channel_id: int) -> Delete:
    return delete(MessageEvent) \
        .where(MessageEvent.channel_id == channel_id)


def delete_users_stat(type_id: int) -> Delete:
    return delete(UserStat) \
        .where(UserStat.type_id == type_id)


def delete_all(model_type: Type[BaseModel]) -> Delete:
    return delete(model_type)
