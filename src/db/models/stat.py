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

from enum import unique
from sqlalchemy import Column, VARCHAR
from .base import BaseModel

class Stat(BaseModel):
    __tablename__ = 'stats'

    name = Column(VARCHAR(63), nullable=False, unique=True)
    value = Column(VARCHAR(255), nullable=False)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",name={0.name!r},value={0.value!r}".format(self)
        return s + f + ")>"
