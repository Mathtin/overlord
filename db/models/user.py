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

from sqlalchemy import Column, Integer, VARCHAR
from .base import BaseModel

class User(BaseModel):
    __tablename__ = 'users'

    did = Column(Integer, nullable=False, unique=True)
    name = Column(VARCHAR(127), nullable=False)
    disc = Column(Integer, nullable=False)
    display_name = Column(VARCHAR(127), nullable=False)
    roles = Column(VARCHAR(127), nullable=True)

    def __repr__(self):
        s = super().__repr__()[:-2]
        f = ",did={0.did!r},name={0.name!r},disc={0.disc!r},display_name={0.display_name!r},roles={0.roles!r}".format(self)
        return s + f + ")>"
