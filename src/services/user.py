#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################
# ........../\./\...___......|\.|..../...\.........#
# ........./..|..\/\.|.|_|._.|.\|....|.c.|.........#
# ......../....../--\|.|.|.|i|..|....\.../.........#
#        Mathtin (c)                              #
###################################################
#   Project: Overlord discord bot                 #
#   Author: Daniel [Mathtin] Shiko                #
#   Copyright (c) 2020 <wdaniil@mail.ru>          #
#   This file is released under the MIT license.  #
###################################################

__author__ = 'Mathtin'

import logging

import discord
import db as DB
import db.converters as conv
import db.queries as q

from typing import Optional, Union
from .role import RoleService

log = logging.getLogger('user-service')


##########################
# Service implementation #
##########################

class UserService(object):
    # Members passed via constructor
    db: DB.DBPersistSession
    roles: RoleService

    def __init__(self, db: DB.DBPersistSession, roles: RoleService) -> None:
        self.db = db
        self.roles = roles
        self.bot_cache = {}

    def mark_everyone_absent(self) -> None:
        self.db.query(DB.User).update({'roles': None, 'display_name': None})
        self.db.commit()

    def update_member(self, member: discord.Member) -> DB.User:
        u_row = conv.member_row(member, self.roles.role_rows_did_map)
        user = self.db.update_or_add(DB.User, 'did', u_row)
        self.db.commit()
        return user

    def add_user(self, user: discord.User) -> DB.User:
        u_row = conv.user_row(user)
        user = self.db.add(DB.User, u_row)
        self.db.commit()
        return user

    def remove_absent(self) -> None:
        self.db.query(DB.User).filter_by(roles=None).delete()
        self.db.commit()

    @staticmethod
    def is_absent(user: DB.User) -> bool:
        return user.roles is None

    def remove(self, member: discord.Member) -> Optional[DB.User]:
        user = self.get(member)
        if user is None:
            return None
        user.delete()
        self.db.commit()
        return user

    def mark_absent(self, member: discord.Member) -> Optional[DB.User]:
        user = self.get(member)
        if user is None:
            return None
        user.roles = None
        user.display_name = None
        self.db.commit()
        return user

    def get(self, d_user: Union[discord.User, discord.Member]) -> Optional[DB.User]:
        return q.get_user_by_did(self.db, d_user.id)

    def get_by_display_name(self, display_name: str) -> Optional[DB.User]:
        return self.db.query(DB.User).filter_by(display_name=display_name).first()

    def get_by_qualified_name(self, qualified_name: str) -> Optional[DB.User]:
        if '#' not in qualified_name:
            raise ValueError(f"Invalid qualified name: {qualified_name}")
        [name, disc] = qualified_name.split('#')
        disc = int(disc)
        return self.db.query(DB.User).filter_by(name=name, disc=disc).first()
