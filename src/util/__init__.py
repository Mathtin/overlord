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

from .extbot import *
from .config import ConfigView, ConfigParser, ConfigManager
from .exceptions import InvalidConfigException, NotCoroutineException
from .resources import get as get_resource

import importlib
import shlex
import discord

#################
# Utility Funcs #
#################

_module_cache = {}
def get_module_element(path: str) -> Any:
    splited_path = path.split('.')
    module_name = '.'.join(splited_path[:-1])
    object_name = splited_path[-1]
    if module_name not in _module_cache:
        _module_cache[module_name] = importlib.import_module(module_name)
    module = _module_cache[module_name]
    return getattr(module, object_name)

def dict_fancy_table(values: dict, key_name='name') -> str:
    if not values:
        return '++\n'*2

    col0 = [key_name] + list(values.keys())
    row_count = len(col0)
    col_names = list(values[col0[-1]].keys())

    to_col = lambda k: [k] + [values[v][k] for v in values]
    table = [col0] + [to_col(k) for k in col_names]

    col_width = lambda col: max(len(str(v)) for v in col)
    cols_width = [col_width(col) for col in table]

    cols_format = [f'{{:{w}}}' for w in cols_width]
    str_row_values = lambda i: [cols_format[j].format(col[i]) for (j,col) in enumerate(table)]
    format_line = lambda i: '| ' + ' | '.join(str_row_values(i)) + ' |\n'
    separator = '+-' + '-+-'.join(['-'*w for w in cols_width]) + '-+\n'

    lines = [format_line(i) for i in range(row_count)]
    return separator + separator.join(lines) + separator

def pretty_days(days: int) -> str:
    _s = lambda x: '' if (x%10) == 1 and x != 11 else 's'
    if days == 0:
        return '0 days'
    res = ''
    years = days // 365
    if years > 0:
        res += f'{years} year{_s(years)} '
        days %= 365
    months = days // 30
    if months > 0:
        res += f'{months} month{_s(months)} '
        days %= 30
    if days > 0:
        res += f'{days} day{_s(days)} '
    return res.strip()

def pretty_seconds(seconds: int) -> str:
    _s = lambda x: '' if (x%10) == 1 and x != 11 else 's'
    if seconds == 0:
        return '0 seconds'
    res = ''
    days = seconds // 86400
    if days > 0:
        seconds %= 86400
        res += pretty_days(days) + ' '
    hours = seconds // 3600
    if hours > 0:
        res += f'{hours} hour{_s(hours)} '
        seconds %= 3600
    mins = seconds // 60
    if mins > 0:
        res += f'{mins} min{_s(mins)} '
        seconds %= 60
    if seconds > 0:
        res += f'{seconds} second{_s(seconds)} '
    return res.strip()

def parse_control_message(prefix: str, message: discord.Message) -> List[str]:
    prefix_len = len(prefix)
    msg = message.content.strip()

    msg_prefix = msg[: prefix_len]
    msg_suffix = msg[prefix_len :]

    if msg_prefix != prefix or msg_suffix == "":
        return None

    lines = [l.strip() for l in msg_suffix.splitlines()]
    res = shlex.split(lines[0])
    lines = lines[1:]
    merging = False
    merging_val = ''
    for line in lines:
        if line[:2] == '> ':
            if merging:
                merging_val += '\n' + line[2:]
            else:
                merging = True
                merging_val = line[2:]
            continue
        elif merging:
            res.append(merging_val)
            merging = False
            merging_val = ''
        res += shlex.split(line)
    if merging:
        res.append(merging_val)

    return res

def limit_traceback(traceback: List[str], from_file: str, offset: int) -> List[str]:
    res = []
    found = False
    effective_offset = 0
    for line in traceback:
        if not found and from_file in line and line.strip().startswith("File"):
            found = True
            res.append(line)
        elif found and line.strip().startswith("File"):
            effective_offset += 1
        if found and effective_offset < offset:
            res.append(line)
    return res

F_MSGS = lambda m: f'{m} messages'
F_REACTIONS = lambda m: f'{m} reactions'
F_DEFAULT = lambda m: str(m)
FORMATTERS = {
    "membership":            pretty_days,
    "new_message_count":     F_MSGS,
    "delete_message_count":  F_MSGS,
    "edit_message_count":    F_MSGS,
    "new_reaction_count":    F_REACTIONS,
    "delete_reaction_count": F_REACTIONS,
    "vc_time":               pretty_seconds,
    "min_weight":            F_DEFAULT,
    "max_weight":            F_DEFAULT,
    "exact_weight":          F_DEFAULT,
    "weight":                F_DEFAULT,
    "messages":              F_DEFAULT,
    "vc":                    pretty_seconds
}
