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

from sqlalchemy import Column, VARCHAR, Integer, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql.schema import Index
from .base import BaseModel


class EventType(BaseModel):
    __tablename__ = 'event_types'

    name = Column(VARCHAR(63), unique=True, nullable=False)
    description = Column(Text, nullable=True, default=None)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",name={0.name!r},description={0.description!r}".format(self)
        return s + f + ")>"


class Event(object):
    __tablename__ = None

    @declared_attr
    def type_id(cls):
        return Column(Integer, ForeignKey('event_types.id', ondelete='CASCADE'), nullable=False)

    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    @declared_attr
    def type(cls):
        return relationship("EventType", lazy="select")

    @declared_attr
    def user(cls):
        return relationship("User", lazy="select", primaryjoin=cls.__tablename__ + ".c.user_id == users.c.id")

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",type_id={0.type_id!r},user_id={0.user_id!r}".format(self)
        return s + f + ")>"


class MemberEvent(Event, BaseModel):
    __tablename__ = 'member_events'
    __table_args__ = (Index('cix_member_events', "user_id", "created_at"),)


class MessageEvent(Event, BaseModel):
    __tablename__ = 'message_events'

    message_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False, index=True)

    __table_args__ = (Index('cix_message_events', "user_id"),)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",message_id={0.message_id!r},channel_id={0.channel_id!r}".format(self)
        return s + f + ")>"


class VoiceChatEvent(Event, BaseModel):
    __tablename__ = 'vc_events'

    channel_id = Column(BigInteger, nullable=False, index=True)

    __table_args__ = (Index('cix_vc_events', "user_id", "channel_id", "created_at"),)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",channel_id={0.channel_id!r}".format(self)
        return s + f + ")>"


class ReactionEvent(Event, BaseModel):
    __tablename__ = 'reaction_events'

    message_event_id = Column(Integer, ForeignKey('message_events.id', ondelete='CASCADE'), nullable=False, index=True)

    message_event = relationship("MessageEvent", lazy="select")

    __table_args__ = (Index('cix_reaction_events', "message_event_id"),)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",message_event_id={0.message_event_id!r}".format(self)
        return s + f + ")>"
