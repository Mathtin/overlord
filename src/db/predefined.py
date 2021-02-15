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

EVENT_TYPES = [
    {'name': 'member_join', 'description': 'user joined DS'},
    {'name': 'member_leave', 'description': 'user left DS by himself'},
    {'name': 'new_message', 'description': 'user posted new message'},
    {'name': 'message_edit', 'description': 'user edited message'},
    {'name': 'message_delete', 'description': 'user deleted message'},
    {'name': 'vc_join', 'description': 'user joined VC'},
    {'name': 'vc_leave', 'description': 'user left VC'},
    {'name': 'new_reaction', 'description': 'user reacted to message'},
    {'name': 'reaction_delete', 'description': 'user removed reaction'},
]

USER_STAT_TYPES = [
    {'name': 'new_message_count', 'description': 'overall message sent count per user'},
    {'name': 'delete_message_count', 'description': 'overall message delete count per user'},
    {'name': 'edit_message_count', 'description': 'overall message edit count per user'},
    {'name': 'new_reaction_count', 'description': 'overall reactions count per user'},
    {'name': 'delete_reaction_count', 'description': 'overall reaction delete count per user'},
    {'name': 'vc_time', 'description': 'overall time spent in voice chat per user in seconds'},
    {'name': 'membership', 'description': 'days user being member of discord server'},
    {'name': 'min_weight', 'description': 'minimal weight (rank) applicable to user'},
    {'name': 'max_weight', 'description': 'maximal weight (rank) applicable to user'},
    {'name': 'exact_weight', 'description': 'exact weight (rank) applicable to user'}
]
