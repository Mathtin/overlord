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

from typing import Dict, List, Optional

log = logging.getLogger('role-service')


##########################
# Service implementation #
##########################

class RoleService(object):
    # State
    role_map: Dict[str, discord.Role]
    role_rows_did_map: Dict[int, DB.Role]

    # Members passed via constructor
    db: DB.DBPersistSession

    def __init__(self, db: DB.DBPersistSession) -> None:
        self.db = db

    def load(self, roles: List[discord.Role]) -> None:
        self.role_map = {role.name: role for role in roles}
        roles = conv.roles_to_rows(roles)
        self.role_rows_did_map = {role['did']: role for role in roles}
        # Sync table
        self.db.sync_table(DB.Role, 'did', roles)

    def get(self, role_name: str) -> Optional[discord.Role]:
        if role_name in self.role_map:
            return self.role_map[role_name]
        return None
