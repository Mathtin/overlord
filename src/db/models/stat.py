#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################
#........../\./\...___......|\.|..../...\.........#
#........./..|..\/\.|.|_|._.|.\|....|.c.|.........#
#......../....../--\|.|.|.|i|..|....\.../.........#
#        Mathtin (c)                              #
###################################################
#   Project: Overlord discord bot                 #
#   Author: Daniel [Mathtin] Shiko                #
#   Copyright (c) 2020 <wdaniil@mail.ru>          #
#   This file is released under the MIT license.  #
###################################################

__author__ = 'Mathtin'

from enum import unique
from sqlalchemy import Column, VARCHAR, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import UniqueConstraint
from .base import BaseModel

class UserStatType(BaseModel):
    __tablename__ = 'user_stat_types'

    name = Column(VARCHAR(63), unique=True, nullable=False)
    description = Column(Text, nullable=True, default=None)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",name={0.name!r},description={0.description!r}".format(self)
        return s + f + ")>"

class UserStat(BaseModel):
    __tablename__ = 'user_stats'
    __table_args__ = (
        UniqueConstraint('user_id', 'type_id', name='unique_user_stat_type'),
    )

    value = Column(Integer, nullable=False)

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    type_id = Column(Integer, ForeignKey('user_stat_types.id', ondelete='CASCADE'), nullable=False, index=True)

    user = relationship("User", lazy="select")
    type = relationship("UserStatType", lazy="select")

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = "user_id={0.user_id!r},type_id={0.type_id!r},value={0.value!r}".format(self)
        return s + f + ")>"
