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

from sqlalchemy import Column, VARCHAR, Integer, BigInteger
from .base import BaseModel

class Role(BaseModel):
    __tablename__ = 'roles'

    did = Column(BigInteger, nullable=False, unique=True)
    name = Column(VARCHAR(63), unique=True, nullable=False)
    idx = Column(Integer, unique=True, nullable=False)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",name={0.name!r},description={0.description!r},idx={0.idx!r}".format(self)
        return s + f + ")>"
