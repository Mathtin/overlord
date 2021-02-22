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

from datetime import datetime
from typing import Any, Dict, List

import discord as d

from .models import User, MessageEvent


#
# Roles
#

def role_to_row(role: d.Role) -> Dict[str, Any]:
    return {
        'did': role.id,
        'name': role.name,
        'created_at': role.created_at
    }


def roles_to_rows(roles: List[d.Role]) -> List[Dict[str, Any]]:
    rows = [role_to_row(r) for r in roles]
    rows = sorted(rows, key=lambda o: o['did'])
    for i in range(len(rows)):
        rows[i]['idx'] = i
    return rows


def role_mask(user: d.Member, role_map: Dict[int, Dict[str, Any]]) -> str:
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


def member_row(user: d.Member, role_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    return {
        'did': user.id,
        'name': user.name,
        'disc': user.discriminator,
        'display_name': user.display_name,
        'roles': role_mask(user, role_map),
        'created_at': user.joined_at
    }


def member_join_row(user: User, joined: datetime, events: Dict[str, int]) -> Dict[str, Any]:
    return {
        'type_id': events["member_join"],
        'user_id': user.id,
        'created_at': joined
    }


def user_leave_row(user: User, events: Dict[str, int]) -> Dict[str, Any]:
    return {
        'type_id': events["member_leave"],
        'user_id': user.id
    }


#
# Messages
#

def new_message_to_row(user_id: int, msg: d.Message, events: Dict[str, int]) -> Dict[str, Any]:
    return {
        'type_id': events["new_message"],
        'user_id': user_id,
        'message_id': msg.id,
        'channel_id': msg.channel.id,
        'created_at': msg.created_at
    }


def message_edit_row(msg: MessageEvent, events: Dict[str, int]) -> Dict[str, Any]:
    return {
        'type_id': events["message_edit"],
        'user_id': msg.user.id,
        'message_id': msg.message_id,
        'channel_id': msg.channel_id
    }


def message_delete_row(msg: MessageEvent, events: Dict[str, int]) -> Dict[str, Any]:
    return {
        'type_id': events["message_delete"],
        'user_id': msg.user.id,
        'message_id': msg.message_id,
        'channel_id': msg.channel_id
    }


#
# VC
#

def vc_join_row(user: User, channel: d.VoiceChannel, events: Dict[str, int]) -> Dict[str, Any]:
    return {
        'type_id': events["vc_join"],
        'user_id': user.id,
        'channel_id': channel.id
    }


def vc_leave_row(user: User, channel: d.VoiceChannel, events: Dict[str, int]) -> Dict[str, Any]:
    return {
        'type_id': events["vc_leave"],
        'user_id': user.id,
        'channel_id': channel.id
    }


#
# Reaction
#

def new_reaction_to_row(user: User, msg: MessageEvent, events: Dict[str, int]) -> Dict[str, Any]:
    return {
        'type_id': events["new_reaction"],
        'user_id': user.id,
        'message_event_id': msg.id
    }


def reaction_delete_row(user: User, msg: MessageEvent, events: Dict[str, int]) -> Dict[str, Any]:
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
