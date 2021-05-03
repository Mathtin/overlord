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
