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

import discord as d
from .models import User, MessageEvent
from datetime import datetime

#
# Roles
#

def role_to_row(role: d.Role):
    return {
        'did': role.id,
        'name': role.name,
        'created_at': role.created_at
    }

def roles_to_rows(roles: list):
    rows = [role_to_row(r) for r in roles]
    rows = sorted(rows, key = lambda i: i['did'])
    for i in range(len(rows)):
        rows[i]['idx'] = i
    return rows

def role_mask(user: d.Member, role_map: dict):
    mask = ['0'] * len(role_map)
    for role in user.roles:
        idx = role_map[role.id]['idx']
        mask[idx] = '1'
    return ''.join(mask)

#
# Users
#

def user_row(user: d.User):
    return {
        'did': user.id,
        'name': user.name,
        'disc': user.discriminator,
        'display_name': None,
        'roles': None
    }

def member_row(user: d.Member, role_map: dict):
    return {
        'did': user.id,
        'name': user.name,
        'disc': user.discriminator,
        'display_name': user.display_name,
        'roles': role_mask(user, role_map)
    }

def member_join_row(user: User, joined: datetime ,events: dict):
    return {
        'type_id': events["member_join"],
        'user_id': user.id,
        'created_at': joined
    }

def user_leave_row(user: User, events: dict):
    return {
        'type_id': events["member_leave"],
        'user_id': user.id
    }
#
# Messages
#

def new_message_to_row(user: User, msg: d.Message, events: dict):
    return {
        'type_id': events["new_message"],
        'user_id': user.id,
        'message_id': msg.id,
        'channel_id': msg.channel.id,
        'created_at': msg.created_at
    }

def message_edit_row(msg: MessageEvent, events: dict):
    return {
        'type_id': events["message_edit"],
        'user_id': msg.user.id,
        'message_id': msg.message_id,
        'channel_id': msg.channel_id
    }

def message_delete_row(msg: MessageEvent, events: dict):
    return {
        'type_id': events["message_edit"],
        'user_id': msg.user.id,
        'message_id': msg.message_id,
        'channel_id': msg.channel_id
    }

#
# VC
#

def vc_join_row(user: User, channel: d.VoiceChannel, events: dict):
    return {
        'type_id': events["vc_join"],
        'user_id': user.id,
        'channel_id': channel.id
    }

def vc_leave_row(user: User, channel: d.VoiceChannel, events: dict):
    return {
        'type_id': events["vc_leave"],
        'user_id': user.id,
        'channel_id': channel.id
    }