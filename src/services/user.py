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
