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
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.dml import Insert, Update
from sqlalchemy.sql.elements import literal_column
from sqlalchemy.sql.selectable import Select
from sqlalchemy.sql.expression import cast
from sqlalchemy.sql.sqltypes import Integer
from sqlalchemy import func, insert, select, update, and_

from .models import *
from .session import DBPersistSession


def date_to_secs_sqlite(col):
    return cast(func.strftime('%s', col), Integer)


def date_to_secs_mysql(col):
    return func.unix_timestamp(col)


MODE_SQLITE = 'sqlite'
MODE_MYSQL = 'mysql'
MODE = MODE_MYSQL


def date_to_secs(col):
    if MODE == MODE_SQLITE:
        return date_to_secs_sqlite(col)
    if MODE == MODE_MYSQL:
        return date_to_secs_mysql(col)


def get_user_by_did(db: DBPersistSession, id_: int) -> User:
    return db.query(User).filter(User.did == id_).first()


def get_msg_by_did(db: DBPersistSession, id_: int) -> MessageEvent:
    return db.query(MessageEvent).filter(MessageEvent.message_id == id_).first()


def get_last_member_event_by_did(db: DBPersistSession, id_: int) -> MessageEvent:
    return db.query(MemberEvent).join(User) \
        .filter(User.did == id_) \
        .order_by(MemberEvent.created_at.desc()).first()


def get_last_member_event_by_id(db: DBPersistSession, id_: int) -> MessageEvent:
    return db.query(MemberEvent) \
        .filter(MemberEvent.user_id == id_) \
        .order_by(MemberEvent.created_at.desc()).first()


def get_last_vc_event_by_id(db: DBPersistSession, id_: int, channel_id: int) -> VoiceChatEvent:
    return db.query(VoiceChatEvent) \
        .filter(and_(VoiceChatEvent.user_id == id_, VoiceChatEvent.channel_id == channel_id)) \
        .order_by(VoiceChatEvent.created_at.desc()).first()


def get_last_vc_event_by_id_and_type_id(db: DBPersistSession, id_: int, channel_id: int,
                                        type_id: int) -> VoiceChatEvent:
    return db.query(VoiceChatEvent) \
        .filter(and_(VoiceChatEvent.user_id == id_,
                     VoiceChatEvent.channel_id == channel_id,
                     VoiceChatEvent.type_id == type_id)) \
        .order_by(VoiceChatEvent.created_at.desc()).first()


def get_user_stat_by_id(db: DBPersistSession, id_: int, type_id: int) -> UserStat:
    return db.query(UserStat) \
        .filter(and_(UserStat.user_id == id_, UserStat.type_id == type_id)).first()


def select_membership_time_per_user(type_id: int, lit_values: list) -> Select:
    join_time = date_to_secs(func.max(MemberEvent.created_at))
    current_time = int(datetime.now().timestamp())
    membership_value = cast((current_time - join_time) / 86400, Integer).label('value')
    lit_columns = [literal_column(str(v)).label(l) for (l, v) in lit_values]
    select_columns = [membership_value, MemberEvent.user_id] + lit_columns
    return select(select_columns).where(and_(MemberEvent.type_id == type_id, User.roles != None)).group_by(
        MemberEvent.user_id)


def select_message_count_per_user(type_id: int, lit_values: list) -> Select:
    value_column = func.count(MessageEvent.id).label('value')
    lit_columns = [literal_column(str(v)).label(l) for (l, v) in lit_values]
    select_columns = [value_column, MessageEvent.user_id] + lit_columns
    return select(select_columns).where(MessageEvent.type_id == type_id).group_by(MessageEvent.user_id)


def select_reaction_count_per_user(type_id: int, lit_values: list) -> Select:
    value_column = func.count(ReactionEvent.id).label('value')
    lit_columns = [literal_column(str(v)).label(l) for (l, v) in lit_values]
    select_columns = [value_column, ReactionEvent.user_id] + lit_columns
    return select(select_columns).where(ReactionEvent.type_id == type_id).group_by(ReactionEvent.user_id)


def select_vc_time_per_user(type_id: int, lit_values: list) -> Select:
    join_time = date_to_secs(VoiceChatEvent.created_at)
    left_time = date_to_secs(VoiceChatEvent.updated_at)
    value_column = func.sum(left_time - join_time).label('value')
    lit_columns = [literal_column(str(v)).label(l) for (l, v) in lit_values]
    select_columns = [value_column, VoiceChatEvent.user_id] + lit_columns
    return select(select_columns).where(VoiceChatEvent.type_id == type_id).group_by(VoiceChatEvent.user_id)


def insert_user_stat_from_select(select_query: Query) -> Insert:
    return insert(UserStat, inline=True).from_select(['value', 'user_id', 'type_id'], select_query)


def update_inc_user_member_stat(stat_id: int) -> Update:
    return update(UserStat).values(value=UserStat.value + 1) \
        .where(UserStat.type_id == stat_id)
