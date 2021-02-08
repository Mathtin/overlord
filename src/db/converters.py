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

from typing import Any, Dict, List
import discord as d
from .models import User, MessageEvent
from datetime import datetime

#
# Roles
#

def role_to_row(role: d.Role) -> Dict[str, Any]:
    return {
        'did': role.id,
        'name': role.name,
        'created_at': role.created_at
    }

def roles_to_rows(roles: list) -> List[Dict[str, Any]]:
    rows = [role_to_row(r) for r in roles]
    rows = sorted(rows, key = lambda i: i['did'])
    for i in range(len(rows)):
        rows[i]['idx'] = i
    return rows

def role_mask(user: d.Member, role_map: dict) -> str:
    mask = ['0'] * len(role_map)
    for role in user.roles:
        idx = role_map[role.id]['idx']
        mask[idx] = '1'
    return ''.join(mask)

#
# Users
#

def user_row(user: d.User) -> Dict[str, Any]:
    return {
        'did': user.id,
        'name': user.name,
        'disc': user.discriminator,
        'display_name': None,
        'roles': None
    }

def member_row(user: d.Member, role_map: dict) -> Dict[str, Any]:
    return {
        'did': user.id,
        'name': user.name,
        'disc': user.discriminator,
        'display_name': user.display_name,
        'roles': role_mask(user, role_map),
        'created_at': user.joined_at
    }

def member_join_row(user: User, joined: datetime ,events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["member_join"],
        'user_id': user.id,
        'created_at': joined
    }

def user_leave_row(user: User, events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["member_leave"],
        'user_id': user.id
    }
#
# Messages
#

def new_message_to_row(user_id: int, msg: d.Message, events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["new_message"],
        'user_id': user_id,
        'message_id': msg.id,
        'channel_id': msg.channel.id,
        'created_at': msg.created_at
    }

def message_edit_row(msg: MessageEvent, events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["message_edit"],
        'user_id': msg.user.id,
        'message_id': msg.message_id,
        'channel_id': msg.channel_id
    }

def message_delete_row(msg: MessageEvent, events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["message_delete"],
        'user_id': msg.user.id,
        'message_id': msg.message_id,
        'channel_id': msg.channel_id
    }

#
# VC
#

def vc_join_row(user: User, channel: d.VoiceChannel, events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["vc_join"],
        'user_id': user.id,
        'channel_id': channel.id
    }

def vc_leave_row(user: User, channel: d.VoiceChannel, events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["vc_leave"],
        'user_id': user.id,
        'channel_id': channel.id
    }

#
# Reaction
#

def new_reaction_to_row(user: User, msg: MessageEvent, events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["new_reaction"],
        'user_id': user.id,
        'message_event_id': msg.id
    }

def reaction_delete_row(user: User, msg: MessageEvent, events: dict) -> Dict[str, Any]:
    return {
        'type_id': events["reaction_delete"],
        'user_id': user.id,
        'message_event_id': msg.id
    }


#
# User Stat
#

def empty_user_stat_row(user_id: int, type_id: int) -> Dict[str, Any]:
    return {
        'type_id': type_id,
        'user_id': user_id,
        'value': 0
    }
