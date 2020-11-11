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
from sqlalchemy.ext.declarative import declared_attr
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
        return Column(Integer, ForeignKey('event_types.id', ondelete='CASCADE'), nullable=False, index=True)
    
    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    @declared_attr
    def type(cls):
        return relationship("EventType", lazy="select")
        
    @declared_attr
    def user(cls):
        return relationship("User", lazy="select", primaryjoin=cls.__tablename__+".c.user_id == users.c.id")

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",type_id={0.type_id!r},user_id={0.user_id!r}".format(self)
        return s + f + ")>"


class MemberEvent(Event, BaseModel):
    __tablename__ = 'member_events'


class MessageEvent(Event, BaseModel):
    __tablename__ = 'message_events'

    message_id = Column(Integer, nullable=False, index=True)
    channel_id = Column(Integer, nullable=False, index=True)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",author_id={0.author_id!r},channel_id={0.channel_id!r}".format(self)
        return s + f + ")>"

class VoiceChatEvent(Event, BaseModel):
    __tablename__ = 'vc_events'

    channel_id = Column(Integer, nullable=False, index=True)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",channel_id={0.channel_id!r}".format(self)
        return s + f + ")>"
