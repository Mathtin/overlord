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

EVENT_TYPES = [
    { 'name': 'member_join', 'description': 'user joined DS' },
    { 'name': 'member_leave', 'description': 'user left DS by himself' },
    { 'name': 'role_add', 'description': 'role applied to user' },
    { 'name': 'role_del', 'description': 'role removed from user' },
    { 'name': 'new_message', 'description': 'user posted new message' },
    { 'name': 'message_edit', 'description': 'user edited message' },
    { 'name': 'message_delete', 'description': 'user deleted message' },
    { 'name': 'vc_join', 'description': 'user joined VC' },
    { 'name': 'vc_leave', 'description': 'user left VC' }
]
