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
