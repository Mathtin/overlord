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

from sqlalchemy import Column, VARCHAR, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from .base import BaseModel


class EventType(BaseModel):
    __tablename__ = 'event_types'

    name = Column(VARCHAR(63), unique=True, nullable=False)
    description = Column(Text, nullable=True, default=None)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",name={0.name!r},description={0.description!r}".format(self)
        return s + f + ")>"


class Event(BaseModel):
    __tablename__ = 'events'

    type_id = Column(Integer, ForeignKey('event_types.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    type = relationship("EventType", lazy="select")
    user = relationship("User", lazy="select")

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",type_id={0.type_id!r},user_id={0.user_id!r}".format(self)
        return s + f + ")>"


class RoleEvent(BaseModel):
    __tablename__ = 'role_events'

    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)

    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    event = relationship("Event", lazy="joined", uselist=False)

    role = relationship("Role", lazy="select")
    object = relationship("User", lazy="select")

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",event_id={0.event_id!r},role_id={0.role_id!r},object_id={0.object_id!r}".format(self)
        return s + f + ")>"


class KickBanEvent(BaseModel):
    __tablename__ = 'kb_events'

    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)

    object_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    is_banned = Column(Boolean, nullable=False)

    event = relationship("Event", lazy="joined", uselist=False)

    object = relationship("User", lazy="select")

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",object_id={0.object_id!r},is_banned={0.is_banned!r}".format(self)
        return s + f + ")>"


class MessageEvent(BaseModel):
    __tablename__ = 'message_events'

    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False, index=True)

    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    channel_id = Column(Integer, nullable=False)

    event = relationship("Event", lazy="joined", uselist=False)

    author = relationship("User", lazy="select")

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",author_id={0.author_id!r},channel_id={0.channel_id!r}".format(self)
        return s + f + ")>"

